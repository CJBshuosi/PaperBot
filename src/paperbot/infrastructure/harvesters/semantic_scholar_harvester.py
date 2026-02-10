# src/paperbot/infrastructure/harvesters/semantic_scholar_harvester.py
"""
Semantic Scholar paper harvester.

Uses the Semantic Scholar Academic Graph API for paper search.
API documentation: https://api.semanticscholar.org/api-docs/
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from paperbot.domain.harvest import HarvestedPaper, HarvestResult, HarvestSource
from paperbot.infrastructure.api_clients.semantic_scholar import SemanticScholarClient

logger = logging.getLogger(__name__)


class SemanticScholarHarvester:
    """
    Semantic Scholar paper harvester.

    API: https://api.semanticscholar.org/graph/v1/paper/search
    Rate limit: 100 req/min (with API key), 5000/day without key
    """

    FIELDS = [
        "paperId",
        "title",
        "abstract",
        "year",
        "venue",
        "citationCount",
        "authors",
        "publicationDate",
        "externalIds",
        "fieldsOfStudy",
        "url",
        "openAccessPdf",
    ]

    def __init__(self, client: Optional[SemanticScholarClient] = None, api_key: Optional[str] = None):
        self.client = client or SemanticScholarClient(api_key=api_key)

    @property
    def source(self) -> HarvestSource:
        return HarvestSource.SEMANTIC_SCHOLAR

    async def search(
        self,
        query: str,
        *,
        max_results: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        venues: Optional[List[str]] = None,
    ) -> HarvestResult:
        """Search Semantic Scholar API."""
        try:
            # S2 API supports year filter in query
            year_filter = ""
            if year_from and year_to:
                year_filter = f" year:{year_from}-{year_to}"
            elif year_from:
                year_filter = f" year:{year_from}-"
            elif year_to:
                year_filter = f" year:-{year_to}"

            results = await self.client.search_papers(
                query=query + year_filter,
                limit=min(max_results, 100),  # S2 limit per request
                fields=self.FIELDS,
            )

            papers = [self._to_paper(r, rank=i) for i, r in enumerate(results)]

            # Filter by venue if specified
            if venues:
                venue_set = {v.lower() for v in venues}
                papers = [
                    p
                    for p in papers
                    if p.venue and any(v in p.venue.lower() for v in venue_set)
                ]

            logger.info(f"Semantic Scholar harvester found {len(papers)} papers for query: {query}")

            return HarvestResult(
                source=self.source,
                papers=papers,
                total_found=len(papers),
            )
        except Exception as e:
            logger.warning(f"Semantic Scholar harvester error: {e}")
            return HarvestResult(
                source=self.source,
                papers=[],
                total_found=0,
                error=str(e),
            )

    def _to_paper(self, data: Dict[str, Any], rank: int) -> HarvestedPaper:
        """Convert S2 API response to HarvestedPaper."""
        authors = [a.get("name", "") for a in data.get("authors", []) if a.get("name")]
        external_ids = data.get("externalIds", {}) or {}

        pdf_url = None
        if data.get("openAccessPdf"):
            pdf_url = data["openAccessPdf"].get("url")

        return HarvestedPaper(
            title=data.get("title", ""),
            source=HarvestSource.SEMANTIC_SCHOLAR,
            abstract=data.get("abstract") or "",
            authors=authors,
            doi=external_ids.get("DOI"),
            arxiv_id=external_ids.get("ArXiv"),
            semantic_scholar_id=data.get("paperId"),
            year=data.get("year"),
            venue=data.get("venue"),
            publication_date=data.get("publicationDate"),
            citation_count=data.get("citationCount", 0) or 0,
            url=data.get("url"),
            pdf_url=pdf_url,
            fields_of_study=data.get("fieldsOfStudy") or [],
            source_rank=rank,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        # SemanticScholarClient manages its own session
        pass
