# src/paperbot/infrastructure/harvesters/arxiv_harvester.py
"""
arXiv paper harvester.

Uses the arXiv Atom API for paper search.
API documentation: https://arxiv.org/help/api
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

import aiohttp

from paperbot.domain.harvest import HarvestedPaper, HarvestResult, HarvestSource
from paperbot.infrastructure.connectors.arxiv_connector import ArxivConnector, ArxivRecord

logger = logging.getLogger(__name__)


class ArxivHarvester:
    """
    arXiv paper harvester using the Atom API.

    API: https://export.arxiv.org/api/query
    Rate limit: 1 request per 3 seconds (be conservative)
    """

    ARXIV_API_URL = "https://export.arxiv.org/api/query"
    REQUEST_INTERVAL = 3.0  # seconds between requests

    def __init__(self, connector: Optional[ArxivConnector] = None):
        self.connector = connector or ArxivConnector()
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request_time: float = 0

    @property
    def source(self) -> HarvestSource:
        return HarvestSource.ARXIV

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        import time

        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.REQUEST_INTERVAL:
            await asyncio.sleep(self.REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def _build_query(
        self,
        query: str,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> str:
        """Build arXiv search query with optional year filters."""
        # arXiv uses submittedDate for filtering
        # Format: submittedDate:[YYYYMMDD TO YYYYMMDD]
        search_query = f"all:{query}"

        if year_from or year_to:
            start_date = f"{year_from}0101" if year_from else "199101"
            end_date = f"{year_to}1231" if year_to else "209912"
            search_query += f" AND submittedDate:[{start_date} TO {end_date}]"

        return search_query

    async def search(
        self,
        query: str,
        *,
        max_results: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        venues: Optional[List[str]] = None,  # Not supported by arXiv
    ) -> HarvestResult:
        """
        Search arXiv using the Atom API.

        Note: arXiv doesn't support venue filtering - all papers are preprints.
        """
        search_query = self._build_query(query, year_from, year_to)

        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": min(max_results, 200),  # arXiv max is ~200 per request
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        try:
            await self._rate_limit()
            session = await self._get_session()

            async with session.get(self.ARXIV_API_URL, params=params) as resp:
                if resp.status != 200:
                    return HarvestResult(
                        source=self.source,
                        papers=[],
                        total_found=0,
                        error=f"arXiv API returned status {resp.status}",
                    )
                xml_text = await resp.text()

            records = self.connector.parse_atom(xml_text)
            papers = [self._record_to_paper(r, rank=i) for i, r in enumerate(records)]

            logger.info(f"arXiv harvester found {len(papers)} papers for query: {query}")

            return HarvestResult(
                source=self.source,
                papers=papers,
                total_found=len(papers),
            )
        except Exception as e:
            logger.warning(f"arXiv harvester error: {e}")
            return HarvestResult(
                source=self.source,
                papers=[],
                total_found=0,
                error=str(e),
            )

    def _record_to_paper(self, record: ArxivRecord, rank: int) -> HarvestedPaper:
        """Convert ArxivRecord to HarvestedPaper."""
        # Extract arxiv_id from full URL (e.g., "http://arxiv.org/abs/2301.12345v1")
        arxiv_id = record.arxiv_id
        if "/" in arxiv_id:
            arxiv_id = arxiv_id.split("/")[-1]
        # Remove version suffix (e.g., "2301.12345v1" -> "2301.12345")
        if "v" in arxiv_id:
            arxiv_id = arxiv_id.split("v")[0]

        # Extract year from published date
        year = None
        if record.published:
            try:
                year = int(record.published[:4])
            except (ValueError, IndexError):
                pass

        return HarvestedPaper(
            title=record.title.replace("\n", " ").strip(),
            source=HarvestSource.ARXIV,
            abstract=record.summary.replace("\n", " ").strip(),
            authors=record.authors,
            arxiv_id=arxiv_id,
            year=year,
            publication_date=record.published[:10] if record.published else None,
            url=record.abs_url,
            pdf_url=record.pdf_url,
            source_rank=rank,
        )

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
