"""
通用 API 客户端封装
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, Any, Optional

try:
    import aiohttp
    from aiohttp import ClientTimeout
except ImportError:
    aiohttp = None
    ClientTimeout = None

logger = logging.getLogger(__name__)


class APIClient:
    """通用异步 HTTP API 客户端"""
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        request_interval: float = 1.0,
    ):
        if aiohttp is None:
            raise RuntimeError("需要安装 aiohttp 库: pip install aiohttp")
        
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = ClientTimeout(total=timeout)
        self.request_interval = request_interval
        self._last_request_time = 0.0
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建 aiohttp session"""
        if self._session is None or self._session.closed:
            headers = {"User-Agent": "PaperBot/1.0"}
            if self.api_key:
                headers["x-api-key"] = self.api_key
            self._session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=headers,
            )
        return self._session
    
    async def _wait_for_rate_limit(self):
        """等待以遵守速率限制"""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.request_interval:
            await asyncio.sleep(self.request_interval - elapsed)
        self._last_request_time = time.time()
    
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """发送 GET 请求，带指数退避重试（429/5xx）"""
        import random

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        last_status = 0

        for attempt in range(max_retries + 1):
            await self._wait_for_rate_limit()
            session = await self._get_session()

            try:
                async with session.get(url, params=params) as response:
                    last_status = response.status
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        logger.warning(f"Resource not found: {url}")
                        return {}
                    elif response.status == 429 or response.status >= 500:
                        # Consume response body to release connection
                        retry_after = response.headers.get("Retry-After")
                        await response.read()
                        # On final attempt, break out to raise below
                        if attempt >= max_retries:
                            break
                        # Exponential backoff with Retry-After support
                        if retry_after:
                            try:
                                delay = min(float(retry_after), 30.0)
                            except (TypeError, ValueError):
                                delay = 2.0 * (2 ** attempt)
                        else:
                            delay = 2.0 * (2 ** attempt)
                        # Add jitter (±25%)
                        jitter = delay * 0.25 * (2 * random.random() - 1)
                        delay = max(1.0, delay + jitter)
                        logger.warning(
                            f"HTTP {response.status} for {url}, "
                            f"retry {attempt + 1}/{max_retries} in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        text = await response.text()
                        logger.error(f"API error {response.status}: {text[:200]}")
                        raise Exception(f"API error: {response.status}")
            except asyncio.TimeoutError:
                if attempt >= max_retries:
                    logger.error(f"Request timeout after {max_retries + 1} attempts: {url}")
                    raise
                delay = 2.0 * (2 ** attempt)
                logger.warning(
                    f"Timeout for {url}, retry {attempt + 1}/{max_retries} in {delay:.1f}s"
                )
                await asyncio.sleep(delay)
                continue

        raise Exception(f"HTTP {last_status} after {max_retries + 1} attempts: {url}")
    
    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """发送 POST 请求"""
        await self._wait_for_rate_limit()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        session = await self._get_session()
        
        try:
            async with session.post(url, data=data, json=json_data) as response:
                if response.status in (200, 201):
                    return await response.json()
                else:
                    text = await response.text()
                    logger.error(f"API error {response.status}: {text[:200]}")
                    raise Exception(f"API error: {response.status}")
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {url}")
            raise
        except Exception as e:
            logger.error(f"Request failed: {url} - {e}")
            raise
    
    async def close(self):
        """关闭 session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

