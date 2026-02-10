# src/paperbot/infrastructure/harvesters/openalex_harvester.py
"""
OpenAlex paper harvester.

Uses the OpenAlex API for paper search.
API documentation: https://docs.openalex.org/
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp

from paperbot.domain.harvest import HarvestedPaper, HarvestResult, HarvestSource

logger = logging.getLogger(__name__)


class OpenAlexHarvester:
    """
    OpenAlex paper harvester.

    API: https://api.openalex.org/works
    Rate limit: 10 req/s (polite pool with email), 100K/day
    """

    OPENALEX_API_URL = "https://api.openalex.org/works"
    REQUEST_INTERVAL = 0.1  # 10 req/s

    def __init__(self, email: Optional[str] = None):
        self.email = email  # For polite pool
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request_time: float = 0

    @property
    def source(self) -> HarvestSource:
        return HarvestSource.OPENALEX

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

    async def search(
        self,
        query: str,
        *,
        max_results: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        venues: Optional[List[str]] = None,
    ) -> HarvestResult:
        """Search OpenAlex API."""
        params: Dict[str, Any] = {
            "search": query,
            "per_page": min(max_results, 200),  # API max is 200
            "sort": "cited_by_count:desc",
        }

        # Add email for polite pool
        if self.email:
            params["mailto"] = self.email

        # Build filter string
        filters = []
        if year_from:
            filters.append(f"publication_year:>={year_from}")
        if year_to:
            filters.append(f"publication_year:<={year_to}")
        if filters:
            params["filter"] = ",".join(filters)

        try:
            await self._rate_limit()
            session = await self._get_session()

            async with session.get(self.OPENALEX_API_URL, params=params) as resp:
                if resp.status != 200:
                    return HarvestResult(
                        source=self.source,
                        papers=[],
                        total_found=0,
                        error=f"OpenAlex API returned status {resp.status}",
                    )
                data = await resp.json()

            results = data.get("results", [])
            papers = [self._to_paper(r, rank=i) for i, r in enumerate(results)]

            # Filter by venue if specified
            if venues:
                venue_set = {v.lower() for v in venues}
                papers = [
                    p
                    for p in papers
                    if p.venue and any(v in p.venue.lower() for v in venue_set)
                ]

            total_found = data.get("meta", {}).get("count", len(papers))
            logger.info(f"OpenAlex harvester found {len(papers)} papers for query: {query}")

            return HarvestResult(
                source=self.source,
                papers=papers,
                total_found=total_found,
            )
        except Exception as e:
            logger.warning(f"OpenAlex harvester error: {e}")
            return HarvestResult(
                source=self.source,
                papers=[],
                total_found=0,
                error=str(e),
            )

    def _to_paper(self, data: Dict[str, Any], rank: int) -> HarvestedPaper:
        """Convert OpenAlex API response to HarvestedPaper."""
        # Extract authors
        authors = []
        for authorship in data.get("authorships", []):
            author = authorship.get("author", {})
            if author.get("display_name"):
                authors.append(author["display_name"])

        # Extract identifiers
        ids = data.get("ids", {})
        doi = ids.get("doi", "")
        if doi:
            doi = doi.replace("https://doi.org/", "")

        openalex_id = ids.get("openalex", "")
        if openalex_id:
            openalex_id = openalex_id.replace("https://openalex.org/", "")

        # Extract venue
        venue = None
        if data.get("primary_location"):
            source = data["primary_location"].get("source") or {}
            venue = source.get("display_name")

        # Extract PDF URL
        pdf_url = None
        if data.get("open_access", {}).get("oa_url"):
            pdf_url = data["open_access"]["oa_url"]

        # Extract keywords from concepts
        keywords = [
            c.get("display_name", "")
            for c in data.get("keywords", [])[:10]
            if c.get("display_name")
        ]

        # Extract fields of study from concepts
        fields_of_study = [
            c.get("display_name", "")
            for c in data.get("concepts", [])[:5]
            if c.get("display_name")
        ]

        return HarvestedPaper(
            title=data.get("title", "") or data.get("display_name", ""),
            source=HarvestSource.OPENALEX,
            abstract=self._get_abstract(data),
            authors=authors,
            doi=doi if doi else None,
            openalex_id=openalex_id if openalex_id else None,
            year=data.get("publication_year"),
            venue=venue,
            publication_date=data.get("publication_date"),
            citation_count=data.get("cited_by_count", 0) or 0,
            url=data.get("doi") or ids.get("openalex"),
            pdf_url=pdf_url,
            keywords=keywords,
            fields_of_study=fields_of_study,
            source_rank=rank,
        )

    def _get_abstract(self, data: Dict[str, Any]) -> str:
        """Reconstruct abstract from inverted index."""
        abstract_index = data.get("abstract_inverted_index")
        if not abstract_index:
            return ""

        # OpenAlex stores abstract as inverted index: {"word": [positions]}
        try:
            words: List[tuple[int, str]] = []
            for word, positions in abstract_index.items():
                for pos in positions:
                    words.append((pos, word))
            words.sort(key=lambda x: x[0])
            return " ".join(w[1] for w in words)
        except Exception:
            return ""

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
