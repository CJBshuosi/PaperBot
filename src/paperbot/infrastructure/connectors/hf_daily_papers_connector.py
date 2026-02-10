from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests


_ARXIV_ID_RE = re.compile(r"^(\d{4}\.\d{4,5})(v\d+)?$")


@dataclass
class HFDailyPaperRecord:
    paper_id: str
    title: str
    summary: str
    published_at: str
    submitted_on_daily_at: str
    authors: List[str]
    ai_keywords: List[str]
    upvotes: int
    paper_url: str
    external_url: str
    pdf_url: str


class HFDailyPapersConnector:
    """Connector for Hugging Face Daily Papers API."""

    def __init__(
        self,
        *,
        base_url: str = "https://huggingface.co",
        timeout_s: float = 20.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self._headers = {"User-Agent": "PaperBot/2.0"}

    def fetch_daily_papers(self, *, limit: int = 100, page: int = 0) -> List[Dict[str, Any]]:
        """Fetch one page of daily papers.

        Hugging Face currently caps `limit` at 100.
        """
        safe_limit = max(1, min(int(limit), 100))
        params = {"limit": safe_limit, "p": max(int(page), 0)}
        url = f"{self.base_url}/api/daily_papers"
        resp = requests.get(url, params=params, headers=self._headers, timeout=self.timeout_s)
        resp.raise_for_status()

        payload = resp.json()
        if not isinstance(payload, list):
            return []
        return payload

    def search(
        self,
        *,
        query: str,
        max_results: int = 25,
        page_size: int = 100,
        max_pages: int = 5,
    ) -> List[HFDailyPaperRecord]:
        tokens = _tokenize_query(query)
        if not tokens:
            return []

        max_pages = max(1, int(max_pages))
        candidates: List[tuple[float, HFDailyPaperRecord]] = []
        seen: set[str] = set()

        for page in range(max_pages):
            rows = self.fetch_daily_papers(limit=page_size, page=page)
            if not rows:
                break

            for raw in rows:
                record = self._parse_record(raw)
                if record is None:
                    continue

                dedupe_key = f"{record.paper_id}|{record.title.lower()}"
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)

                text = " ".join(
                    [record.title, record.summary, " ".join(record.ai_keywords)]
                ).lower()
                hit_count = sum(1 for token in tokens if token and token in text)
                if hit_count <= 0:
                    continue

                score = float(hit_count) * 10.0 + float(record.upvotes) * 0.2
                candidates.append((score, record))

            # Early stop when we already have enough matched papers.
            if len(candidates) >= max_results:
                break

        candidates.sort(
            key=lambda pair: (
                pair[0],
                _date_sort_key(pair[1].submitted_on_daily_at),
                pair[1].upvotes,
            ),
            reverse=True,
        )
        return [record for _, record in candidates[: max(int(max_results), 0)]]

    def _parse_record(self, raw: Dict[str, Any]) -> Optional[HFDailyPaperRecord]:
        if not isinstance(raw, dict):
            return None

        paper_obj = raw.get("paper")
        if not isinstance(paper_obj, dict):
            paper_obj = raw

        paper_id = str(paper_obj.get("id") or "").strip()
        title = str(paper_obj.get("title") or raw.get("title") or "").strip()
        if not paper_id or not title:
            return None

        summary = str(paper_obj.get("summary") or raw.get("summary") or "").strip()
        published_at = str(paper_obj.get("publishedAt") or raw.get("publishedAt") or "").strip()
        submitted_on_daily_at = str(paper_obj.get("submittedOnDailyAt") or "").strip()
        upvotes = int(paper_obj.get("upvotes") or 0)

        authors: List[str] = []
        for author in paper_obj.get("authors") or []:
            if isinstance(author, dict):
                name = str(author.get("name") or "").strip()
            else:
                name = str(author or "").strip()
            if name:
                authors.append(name)

        ai_keywords = [
            str(keyword).strip()
            for keyword in (paper_obj.get("ai_keywords") or [])
            if str(keyword).strip()
        ]

        paper_url = f"{self.base_url}/papers/{paper_id}"
        external_url, pdf_url = _build_external_links(paper_id)

        return HFDailyPaperRecord(
            paper_id=paper_id,
            title=title,
            summary=summary,
            published_at=published_at,
            submitted_on_daily_at=submitted_on_daily_at,
            authors=authors,
            ai_keywords=ai_keywords,
            upvotes=upvotes,
            paper_url=paper_url,
            external_url=external_url,
            pdf_url=pdf_url,
        )


def _build_external_links(paper_id: str) -> tuple[str, str]:
    compact_id = (paper_id or "").strip()
    match = _ARXIV_ID_RE.match(compact_id)
    if not match:
        return "", ""

    normalized = match.group(1) + (match.group(2) or "")
    return (
        f"https://arxiv.org/abs/{normalized}",
        f"https://arxiv.org/pdf/{normalized}.pdf",
    )


def _tokenize_query(query: str) -> List[str]:
    seen = set()
    tokens: List[str] = []
    for token in re.findall(r"[a-z0-9]+", (query or "").lower()):
        if token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def _date_sort_key(value: str) -> datetime:
    text = (value or "").strip()
    if not text:
        return datetime.min
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.min
