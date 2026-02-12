# src/paperbot/application/workflows/harvest_pipeline.py
"""
Paper Harvest Pipeline.

Orchestrates multi-source paper harvesting with deduplication and storage.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from paperbot.domain.harvest import (
    HarvestSource,
)
from paperbot.application.services import (
    QueryRewriter,
    VenueRecommender,
)
from paperbot.application.services.paper_search_service import PaperSearchService
from paperbot.application.workflows.unified_topic_search import make_default_search_service
from paperbot.infrastructure.stores.paper_store import PaperStore

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class HarvestProgress:
    """Progress update during harvesting."""

    phase: str
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class HarvestConfig:
    """Configuration for a harvest run."""

    keywords: List[str]
    venues: Optional[List[str]] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    sources: Optional[List[str]] = None
    max_results_per_source: int = 50
    expand_keywords: bool = True
    recommend_venues: bool = True


@dataclass
class HarvestFinalResult:
    """Final result of a harvest run."""

    run_id: str
    status: str  # success, partial, failed
    papers_found: int
    papers_new: int
    papers_deduplicated: int
    source_results: Dict[str, Dict[str, Any]]
    errors: Dict[str, str]
    duration_seconds: float


class HarvestPipeline:
    """
    Multi-source paper harvest pipeline.

    Orchestrates:
    1. Query expansion (QueryRewriter)
    2. Venue recommendation (VenueRecommender)
    3. Unified search via PaperSearchService (dedup + persist included)
    4. Harvest run record management
    """

    def __init__(
        self,
        db_url: Optional[str] = None,
        *,
        venue_config_path: Optional[str] = None,
        search_service: Optional[PaperSearchService] = None,
    ):
        self.db_url = db_url
        self._venue_config_path = venue_config_path

        # Services (initialized lazily)
        self._query_rewriter: Optional[QueryRewriter] = None
        self._venue_recommender: Optional[VenueRecommender] = None
        self._paper_store: Optional[PaperStore] = None
        self._search_service = search_service

    @property
    def query_rewriter(self) -> QueryRewriter:
        if self._query_rewriter is None:
            self._query_rewriter = QueryRewriter()
        return self._query_rewriter

    @property
    def venue_recommender(self) -> VenueRecommender:
        if self._venue_recommender is None:
            self._venue_recommender = VenueRecommender(
                config_path=self._venue_config_path
            )
        return self._venue_recommender

    @property
    def paper_store(self) -> PaperStore:
        if self._paper_store is None:
            self._paper_store = PaperStore(self.db_url)
        return self._paper_store

    @property
    def search_service(self) -> PaperSearchService:
        if self._search_service is None:
            self._search_service = make_default_search_service(registry=self.paper_store)
        return self._search_service

    @staticmethod
    def new_run_id() -> str:
        """Generate a new harvest run ID."""
        timestamp = _utcnow().strftime("%Y%m%d-%H%M%S")
        suffix = uuid.uuid4().hex[:8]
        return f"harvest-{timestamp}-{suffix}"

    async def run(
        self,
        config: HarvestConfig,
        *,
        run_id: Optional[str] = None,
    ) -> AsyncGenerator[HarvestProgress | HarvestFinalResult, None]:
        """
        Execute harvest pipeline with progress updates.

        Yields:
            HarvestProgress for intermediate updates
            HarvestFinalResult as final yield
        """
        run_id = run_id or self.new_run_id()
        start_time = _utcnow()
        errors: Dict[str, str] = {}
        source_results: Dict[str, Dict[str, Any]] = {}

        # Determine sources to use
        sources = config.sources or [s.value for s in HarvestSource]

        try:
            # Phase 1: Expand keywords
            yield HarvestProgress(
                phase="Expanding",
                message="Expanding keywords...",
            )

            expanded_keywords = config.keywords.copy()
            if config.expand_keywords:
                expanded_keywords = self.query_rewriter.expand_all(config.keywords)
                logger.info(f"Expanded keywords: {config.keywords} → {expanded_keywords}")

            # Phase 2: Recommend venues (if not specified)
            venues = config.venues
            if config.recommend_venues and not venues:
                yield HarvestProgress(
                    phase="Recommending",
                    message="Recommending venues...",
                )
                venues = self.venue_recommender.recommend(
                    expanded_keywords, max_venues=5
                )
                logger.info(f"Recommended venues: {venues}")

            # Phase 3: Create harvest run record
            yield HarvestProgress(
                phase="Initializing",
                message="Creating harvest run record...",
            )

            self.paper_store.create_harvest_run(
                run_id=run_id,
                keywords=expanded_keywords,
                venues=venues or [],
                sources=sources,
                max_results_per_source=config.max_results_per_source,
            )

            # Phase 4: Search via PaperSearchService (handles dedup + persist)
            search_query = " ".join(expanded_keywords)

            yield HarvestProgress(
                phase="Harvesting",
                message=f"Searching {len(sources)} sources via PaperSearchService...",
                details={"sources": sources},
            )

            try:
                search_result = await self.search_service.search(
                    search_query,
                    sources=sources,
                    max_results=config.max_results_per_source * len(sources),
                    year_from=config.year_from,
                    year_to=config.year_to,
                    persist=True,
                )
                papers_found = search_result.total_raw
                papers_new = len(search_result.papers)
                deduplicated_count = search_result.duplicates_removed

                for src in sources:
                    src_papers = [
                        p for p in search_result.papers
                        if src in search_result.provenance.get(p.title_hash or p.title, [])
                    ]
                    source_results[src] = {"papers": len(src_papers), "error": None}

                logger.info(
                    f"PaperSearchService returned {papers_new} unique papers "
                    f"({deduplicated_count} duplicates removed)"
                )
            except Exception as e:
                error_msg = str(e)
                errors["search_service"] = error_msg
                logger.exception(f"PaperSearchService failed: {e}")
                papers_found = 0
                papers_new = 0
                deduplicated_count = 0

            # Phase 5: Update harvest run record
            status = "success"
            if errors:
                status = "partial" if papers_new else "failed"

            self.paper_store.update_harvest_run(
                run_id=run_id,
                status=status,
                papers_found=papers_found,
                papers_new=papers_new,
                papers_deduplicated=deduplicated_count,
                errors=errors if errors else None,
            )

            # Calculate duration
            end_time = _utcnow()
            duration = (end_time - start_time).total_seconds()

            # Yield final result
            yield HarvestFinalResult(
                run_id=run_id,
                status=status,
                papers_found=papers_found,
                papers_new=papers_new,
                papers_deduplicated=deduplicated_count,
                source_results=source_results,
                errors=errors,
                duration_seconds=duration,
            )

        except Exception as e:
            # Handle pipeline-level errors
            logger.exception(f"Harvest pipeline failed: {e}")
            self.paper_store.update_harvest_run(
                run_id=run_id,
                status="failed",
                errors={"pipeline": str(e)},
            )

            end_time = _utcnow()
            duration = (end_time - start_time).total_seconds()

            yield HarvestFinalResult(
                run_id=run_id,
                status="failed",
                papers_found=0,
                papers_new=0,
                papers_deduplicated=0,
                source_results=source_results,
                errors={"pipeline": str(e), **errors},
                duration_seconds=duration,
            )

    async def run_sync(
        self,
        config: HarvestConfig,
        *,
        run_id: Optional[str] = None,
    ) -> HarvestFinalResult:
        """
        Execute harvest pipeline and return only final result.

        Useful for CLI or non-streaming use cases.
        """
        result: Optional[HarvestFinalResult] = None
        async for item in self.run(config, run_id=run_id):
            if isinstance(item, HarvestFinalResult):
                result = item

        if result is None:
            raise RuntimeError("Pipeline completed without final result")
        return result

    async def close(self) -> None:
        """Release all resources."""
        if self._search_service:
            try:
                await self._search_service.close()
            except Exception:
                pass
            self._search_service = None

        if self._paper_store:
            self._paper_store.close()
            self._paper_store = None

    async def __aenter__(self) -> "HarvestPipeline":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
