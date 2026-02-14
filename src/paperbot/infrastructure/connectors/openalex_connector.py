from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

from paperbot.domain.paper_identity import normalize_arxiv_id, normalize_doi


class OpenAlexConnector:
    """Minimal OpenAlex work lookup for graph-style discovery expansion."""

    def __init__(self, *, timeout_s: float = 30.0, base_url: str = "https://api.openalex.org"):
        self.timeout_s = timeout_s
        self.base_url = base_url.rstrip("/")
        self._headers = {"User-Agent": "PaperBot/2.0"}

    def resolve_work(self, *, seed_type: str, seed_id: str) -> Optional[Dict[str, Any]]:
        seed_type = str(seed_type or "").strip().lower()
        seed_id = str(seed_id or "").strip()
        if not seed_id:
            return None

        if seed_type == "openalex":
            return self.get_work(seed_id)
        if seed_type == "doi":
            return self._search_one(f"doi:{normalize_doi(seed_id) or seed_id}")
        if seed_type == "arxiv":
            arxiv_id = normalize_arxiv_id(seed_id) or seed_id
            return self._search_one(f"locations.landing_page_url:https://arxiv.org/abs/{arxiv_id}")
        if seed_type == "semantic_scholar":
            return self._search_one(f"ids.semantic_scholar:{seed_id}")
        return None

    def get_work(self, work_id: str) -> Optional[Dict[str, Any]]:
        resolved = self._normalize_work_id(work_id)
        if not resolved:
            return None
        url = f"{self.base_url}/works/{quote(resolved)}"
        response = requests.get(url, headers=self._headers, timeout=self.timeout_s)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else None

    def get_related_works(self, work: Dict[str, Any], *, limit: int = 20) -> List[Dict[str, Any]]:
        ids = []
        for item in work.get("related_works") or []:
            if isinstance(item, str):
                ids.append(item)
            if len(ids) >= max(1, int(limit)):
                break
        return self.get_works_by_ids(ids, limit=limit)

    def get_referenced_works(
        self, work: Dict[str, Any], *, limit: int = 20
    ) -> List[Dict[str, Any]]:
        ids = []
        for item in work.get("referenced_works") or []:
            if isinstance(item, str):
                ids.append(item)
            if len(ids) >= max(1, int(limit)):
                break
        return self.get_works_by_ids(ids, limit=limit)

    def get_citing_works(self, work: Dict[str, Any], *, limit: int = 20) -> List[Dict[str, Any]]:
        cited_by_api_url = str(work.get("cited_by_api_url") or "").strip()
        if not cited_by_api_url:
            return []
        response = requests.get(
            cited_by_api_url,
            headers=self._headers,
            params={"per-page": max(1, min(int(limit), 200))},
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            return []
        rows = payload.get("results")
        return rows if isinstance(rows, list) else []

    def get_works_by_ids(self, ids: List[str], *, limit: int = 20) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for raw_id in ids[: max(1, int(limit))]:
            work = self.get_work(raw_id)
            if work:
                rows.append(work)
        return rows

    def _search_one(self, filter_expr: str) -> Optional[Dict[str, Any]]:
        response = requests.get(
            f"{self.base_url}/works",
            headers=self._headers,
            params={"filter": filter_expr, "per-page": 1},
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            return None
        rows = payload.get("results")
        if not isinstance(rows, list) or not rows:
            return None
        first = rows[0]
        return first if isinstance(first, dict) else None

    @staticmethod
    def _normalize_work_id(value: str) -> Optional[str]:
        text = str(value or "").strip()
        if not text:
            return None
        lowered = text.lower()
        marker = "openalex.org/"
        idx = lowered.find(marker)
        if idx >= 0:
            text = text[idx + len(marker) :]
        text = text.strip().strip("/")
        if not text:
            return None
        if text[0].upper() != "W":
            text = f"W{text}"
        return text.upper()
