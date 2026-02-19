"""OpenAlex SearchPort adapter."""

from __future__ import annotations

from typing import List, Optional

from paperbot.domain.identity import PaperIdentity
from paperbot.domain.paper import PaperCandidate
from paperbot.infrastructure.harvesters.openalex_harvester import OpenAlexHarvester


class OpenAlexAdapter:
    """SearchPort implementation wrapping OpenAlexHarvester."""

    def __init__(self, harvester: Optional[OpenAlexHarvester] = None):
        self._harvester = harvester or OpenAlexHarvester()

    @property
    def source_name(self) -> str:
        return "openalex"

    async def search(
        self,
        query: str,
        *,
        max_results: int = 30,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> List[PaperCandidate]:
        result = await self._harvester.search(
            query, max_results=max_results, year_from=year_from, year_to=year_to
        )
        return [self._to_candidate(p) for p in result.papers]

    @staticmethod
    def _to_candidate(p) -> PaperCandidate:
        identities: list[PaperIdentity] = []
        if p.openalex_id:
            identities.append(PaperIdentity("openalex", p.openalex_id))
        if p.doi:
            identities.append(PaperIdentity("doi", p.doi))
        if p.arxiv_id:
            identities.append(PaperIdentity("arxiv", p.arxiv_id))
        return PaperCandidate(
            title=p.title,
            abstract=p.abstract,
            authors=p.authors,
            year=p.year,
            venue=p.venue,
            citation_count=p.citation_count,
            url=p.url,
            pdf_url=p.pdf_url,
            keywords=p.keywords,
            fields_of_study=p.fields_of_study,
            publication_date=p.publication_date,
            identities=identities,
        )

    async def close(self) -> None:
        await self._harvester.close()
