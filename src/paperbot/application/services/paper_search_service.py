"""PaperSearchService — unified search facade across all data sources."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from paperbot.application.ports.paper_search_port import SearchPort
from paperbot.domain.paper import PaperCandidate

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Aggregated search result from PaperSearchService."""

    papers: List[PaperCandidate] = field(default_factory=list)
    provenance: Dict[str, List[str]] = field(default_factory=dict)
    total_raw: int = 0
    duplicates_removed: int = 0

    def to_legacy_format(self) -> List[Dict[str, Any]]:
        """Convert to the dict-list format used by existing code."""
        return [p.to_dict() for p in self.papers]


class PaperSearchService:
    """Facade that fans out queries to multiple SearchPort adapters,
    deduplicates, and optionally persists results."""

    def __init__(
        self,
        adapters: Dict[str, SearchPort],
        deduplicator=None,
        registry=None,
        identity_store=None,
    ):
        self._adapters = adapters
        self._deduplicator = deduplicator
        self._registry = registry
        self._identity_store = identity_store

    async def search(
        self,
        query: str,
        *,
        sources: Optional[List[str]] = None,
        max_results: int = 30,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        persist: bool = True,
    ) -> SearchResult:
        """Fan-out search across selected adapters, deduplicate, optionally persist."""
        selected = self._select_adapters(sources)
        if not selected:
            return SearchResult()

        # 1. Concurrent search across adapters
        tasks = [
            adapter.search(
                query,
                max_results=max_results,
                year_from=year_from,
                year_to=year_to,
            )
            for adapter in selected
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_papers: List[PaperCandidate] = []
        provenance: Dict[str, List[str]] = {}

        for adapter, result in zip(selected, results):
            if isinstance(result, Exception):
                logger.warning(f"Adapter {adapter.source_name} failed: {result}")
                continue
            for paper in result:
                all_papers.append(paper)
                key = paper.title_hash or paper.title
                provenance.setdefault(key, []).append(adapter.source_name)

        total_raw = len(all_papers)

        # 2. Deduplicate by title_hash
        seen_hashes: set[str] = set()
        unique: List[PaperCandidate] = []
        for p in all_papers:
            h = p.title_hash
            if h and h in seen_hashes:
                continue
            if h:
                seen_hashes.add(h)
            unique.append(p)

        duplicates_removed = total_raw - len(unique)

        # 3. Persist if requested
        if persist and self._registry:
            for paper in unique:
                try:
                    result_dict = self._registry.upsert_paper(
                        paper=paper.to_dict(),
                        source_hint=provenance.get(paper.title_hash, ["unknown"])[0],
                    )
                    paper.canonical_id = result_dict.get("id")
                except Exception as e:
                    logger.warning(f"Failed to persist paper '{paper.title[:50]}': {e}")

        return SearchResult(
            papers=unique[:max_results],
            provenance=provenance,
            total_raw=total_raw,
            duplicates_removed=duplicates_removed,
        )

    def _select_adapters(self, sources: Optional[List[str]]) -> List[SearchPort]:
        if sources is None:
            return list(self._adapters.values())
        return [
            self._adapters[s]
            for s in sources
            if s in self._adapters
        ]

    async def close(self) -> None:
        for adapter in self._adapters.values():
            try:
                await adapter.close()
            except Exception:
                pass
