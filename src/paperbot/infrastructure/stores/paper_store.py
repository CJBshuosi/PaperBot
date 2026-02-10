<<<<<<< HEAD
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import desc, func, select

from paperbot.domain.paper_identity import normalize_arxiv_id, normalize_doi
from paperbot.infrastructure.stores.models import Base, PaperJudgeScoreModel, PaperModel
=======
# src/paperbot/infrastructure/stores/paper_store.py
"""
Paper storage repository.

Handles persistence and retrieval of harvested papers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import Integer, cast, func, or_, select

from paperbot.utils.logging_config import Logger, LogFiles
from paperbot.domain.harvest import HarvestedPaper, HarvestSource
from paperbot.infrastructure.stores.models import (
    Base,
    HarvestRunModel,
    PaperFeedbackModel,
    PaperModel,
)
>>>>>>> 09ca42d (feat(Harvest): add -- Paper Search and Storage)
from paperbot.infrastructure.stores.sqlalchemy_db import SessionProvider, get_db_url


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


<<<<<<< HEAD
def _safe_list(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    return [str(v).strip() for v in values if str(v).strip()]


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None

    text = str(value).strip()
    if not text:
        return None

    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class SqlAlchemyPaperStore:
    """Canonical paper registry with idempotent upsert for daily workflows."""
=======
@dataclass
class LibraryPaper:
    """Paper with library metadata (saved_at, track_id, action)."""

    paper: PaperModel
    saved_at: datetime
    track_id: Optional[int]
    action: str


class PaperStore:
    """
    Paper storage repository.

    Handles:
    - Batch upsert with DB-level deduplication
    - Filter-based search with pagination
    - Source tracking
    - User library (saved papers)
    """
>>>>>>> 09ca42d (feat(Harvest): add -- Paper Search and Storage)

    def __init__(self, db_url: Optional[str] = None, *, auto_create_schema: bool = True):
        self.db_url = db_url or get_db_url()
        self._provider = SessionProvider(self.db_url)
        if auto_create_schema:
            Base.metadata.create_all(self._provider.engine)

<<<<<<< HEAD
    def upsert_paper(
        self,
        *,
        paper: Dict[str, Any],
        source_hint: Optional[str] = None,
        seen_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        now = _utcnow()
        first_seen = seen_at or now

        title = str(paper.get("title") or "").strip()
        url = str(paper.get("url") or "").strip()
        external_url = str(paper.get("external_url") or "").strip()
        pdf_url = str(paper.get("pdf_url") or "").strip()
        abstract = str(paper.get("snippet") or paper.get("abstract") or "").strip()

        arxiv_id = (
            normalize_arxiv_id(paper.get("arxiv_id"))
            or normalize_arxiv_id(paper.get("paper_id"))
            or normalize_arxiv_id(url)
            or normalize_arxiv_id(external_url)
            or normalize_arxiv_id(pdf_url)
        )
        doi = (
            normalize_doi(paper.get("doi"))
            or normalize_doi(url)
            or normalize_doi(external_url)
            or normalize_doi(pdf_url)
        )

        source = (
            source_hint
            or (paper.get("sources") or [None])[0]
            or paper.get("source")
            or "papers_cool"
        )
        venue = str(paper.get("subject_or_venue") or paper.get("venue") or "").strip()
        published_at = _parse_datetime(
            paper.get("published_at") or paper.get("published") or paper.get("publicationDate")
        )

        authors = _safe_list(paper.get("authors"))
        keywords = _safe_list(paper.get("keywords"))

        metadata = {
            "paper_id": paper.get("paper_id"),
            "matched_queries": _safe_list(paper.get("matched_queries")),
            "branches": _safe_list(paper.get("branches")),
            "score": paper.get("score"),
            "pdf_stars": paper.get("pdf_stars"),
            "kimi_stars": paper.get("kimi_stars"),
            "alternative_urls": _safe_list(paper.get("alternative_urls")),
        }

        with self._provider.session() as session:
            # TODO: title+url fallback query uses scalar_one_or_none() which
            #  raises MultipleResultsFound if duplicates exist. Switch to
            #  .first() or add .limit(1) for safety.
            row = None
            if arxiv_id:
                row = session.execute(
                    select(PaperModel).where(PaperModel.arxiv_id == arxiv_id)
                ).scalar_one_or_none()
            if row is None and doi:
                row = session.execute(
                    select(PaperModel).where(PaperModel.doi == doi)
                ).scalar_one_or_none()
            if row is None and url:
                row = session.execute(
                    select(PaperModel).where(PaperModel.url == url)
                ).scalar_one_or_none()
            if row is None and title:
                row = session.execute(
                    select(PaperModel).where(
                        func.lower(PaperModel.title) == title.lower(),
                        PaperModel.url == url,
                    )
                ).scalar_one_or_none()

            created = row is None
            if row is None:
                row = PaperModel(
                    first_seen_at=_as_utc(first_seen) or now,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)

            # Keep earliest first_seen_at for existing records.
            existing_seen = _as_utc(row.first_seen_at)
            candidate_seen = _as_utc(first_seen) or now
            if not existing_seen or candidate_seen < existing_seen:
                row.first_seen_at = candidate_seen

            if arxiv_id:
                row.arxiv_id = arxiv_id
            if doi:
                row.doi = doi

            row.title = title or row.title or ""
            row.abstract = abstract or row.abstract or ""
            row.url = url or row.url or ""
            row.external_url = external_url or row.external_url or ""
            row.pdf_url = pdf_url or row.pdf_url or ""
            row.source = str(source or row.source or "papers_cool")
            row.venue = venue or row.venue or ""
            row.published_at = _as_utc(published_at) or _as_utc(row.published_at)
            # TODO: unconditional set_authors/set_keywords/set_metadata may wipe
            #  existing data when new paper dict has empty values. Consider
            #  preserving existing values when incoming data is empty:
            #    row.set_authors(authors or row.get_authors())
            row.set_authors(authors)
            row.set_keywords(keywords)
            row.set_metadata(metadata)
            row.updated_at = now

            session.commit()
            session.refresh(row)

            payload = self._paper_to_dict(row)
            payload["_created"] = created
            return payload

    def upsert_many(
        self,
        *,
        papers: Iterable[Dict[str, Any]],
        source_hint: Optional[str] = None,
        seen_at: Optional[datetime] = None,
    ) -> Dict[str, int]:
        created = 0
        updated = 0
        total = 0

        for paper in papers:
            if not isinstance(paper, dict):
                continue
            result = self.upsert_paper(paper=paper, source_hint=source_hint, seen_at=seen_at)
            total += 1
            if result.get("_created"):
                created += 1
            else:
                updated += 1

        return {"total": total, "created": created, "updated": updated}

    def list_recent(self, *, limit: int = 50, source: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._provider.session() as session:
            stmt = select(PaperModel)
            if source:
                stmt = stmt.where(PaperModel.source == source)
            stmt = stmt.order_by(desc(PaperModel.first_seen_at), desc(PaperModel.id)).limit(
                max(1, int(limit))
            )
            rows = session.execute(stmt).scalars().all()
            return [self._paper_to_dict(row) for row in rows]

    def upsert_judge_scores_from_report(self, report: Dict[str, Any]) -> Dict[str, int]:
        now = _utcnow()
        scored_at = _parse_datetime(report.get("generated_at")) or now

        created = 0
        updated = 0
        total = 0

        for query in report.get("queries") or []:
            query_name = str(query.get("normalized_query") or query.get("raw_query") or "").strip()
            if not query_name:
                continue
            for item in query.get("top_items") or []:
                if not isinstance(item, dict):
                    continue
                judge = item.get("judge")
                if not isinstance(judge, dict):
                    continue

                paper_row = self.upsert_paper(
                    paper=item,
                    source_hint=(report.get("sources") or [report.get("source")])[0],
                    seen_at=scored_at,
                )
                paper_db_id = int(paper_row.get("id") or 0)
                if paper_db_id <= 0:
                    continue

                total += 1
                with self._provider.session() as session:
                    row = session.execute(
                        select(PaperJudgeScoreModel).where(
                            PaperJudgeScoreModel.paper_id == paper_db_id,
                            PaperJudgeScoreModel.query == query_name,
                        )
                    ).scalar_one_or_none()

                    was_created = row is None
                    if row is None:
                        row = PaperJudgeScoreModel(
                            paper_id=paper_db_id,
                            query=query_name,
                            scored_at=scored_at,
                        )
                        session.add(row)

                    row.overall = _safe_float(judge.get("overall"))
                    row.relevance = _safe_float((judge.get("relevance") or {}).get("score"))
                    row.novelty = _safe_float((judge.get("novelty") or {}).get("score"))
                    row.rigor = _safe_float((judge.get("rigor") or {}).get("score"))
                    row.impact = _safe_float((judge.get("impact") or {}).get("score"))
                    row.clarity = _safe_float((judge.get("clarity") or {}).get("score"))
                    row.recommendation = str(judge.get("recommendation") or "")
                    row.one_line_summary = str(judge.get("one_line_summary") or "")
                    row.judge_model = str(judge.get("judge_model") or "")
                    try:
                        row.judge_cost_tier = (
                            int(judge.get("judge_cost_tier"))
                            if judge.get("judge_cost_tier") is not None
                            else None
                        )
                    except (ValueError, TypeError):
                        row.judge_cost_tier = None
                    row.scored_at = scored_at
                    row.metadata_json = "{}"

                    session.commit()
                    if was_created:
                        created += 1
                    else:
                        updated += 1

        return {"total": total, "created": created, "updated": updated}

    @staticmethod
    def _paper_to_dict(row: PaperModel) -> Dict[str, Any]:
        return {
            "id": int(row.id),
            "arxiv_id": row.arxiv_id,
            "doi": row.doi,
            "title": row.title,
            "authors": row.get_authors(),
            "abstract": row.abstract,
            "url": row.url,
            "external_url": row.external_url,
            "pdf_url": row.pdf_url,
            "source": row.source,
            "venue": row.venue,
            "published_at": row.published_at.isoformat() if row.published_at else None,
            "first_seen_at": row.first_seen_at.isoformat() if row.first_seen_at else None,
            "keywords": row.get_keywords(),
            "metadata": row.get_metadata(),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
=======
    def upsert_papers_batch(
        self,
        papers: List[HarvestedPaper],
    ) -> Tuple[int, int]:
        """
        Upsert papers with deduplication.

        Returns:
            Tuple of (new_count, updated_count)
        """
        Logger.info(f"Starting batch upsert for {len(papers)} papers", file=LogFiles.HARVEST)
        new_count = 0
        updated_count = 0
        now = _utcnow()

        with self._provider.session() as session:
            for paper in papers:
                Logger.info("Checking for existing paper in database", file=LogFiles.HARVEST)
                existing = self._find_existing(session, paper)

                if existing:
                    Logger.info("Found existing paper, updating metadata", file=LogFiles.HARVEST)
                    self._update_paper(existing, paper, now)
                    updated_count += 1
                else:
                    Logger.info("No existing paper found, creating new record", file=LogFiles.HARVEST)
                    model = self._create_model(paper, now)
                    session.add(model)
                    new_count += 1

            Logger.info("Committing transaction to database", file=LogFiles.HARVEST)
            session.commit()

        Logger.info(f"Batch upsert complete: {new_count} new, {updated_count} updated", file=LogFiles.HARVEST)
        return new_count, updated_count

    def _find_existing(self, session, paper: HarvestedPaper) -> Optional[PaperModel]:
        """Find existing paper by canonical identifiers."""
        # Try each identifier in priority order
        if paper.doi:
            result = session.execute(
                select(PaperModel).where(PaperModel.doi == paper.doi)
            ).scalar_one_or_none()
            if result:
                return result

        if paper.arxiv_id:
            result = session.execute(
                select(PaperModel).where(PaperModel.arxiv_id == paper.arxiv_id)
            ).scalar_one_or_none()
            if result:
                return result

        if paper.semantic_scholar_id:
            result = session.execute(
                select(PaperModel).where(
                    PaperModel.semantic_scholar_id == paper.semantic_scholar_id
                )
            ).scalar_one_or_none()
            if result:
                return result

        if paper.openalex_id:
            result = session.execute(
                select(PaperModel).where(PaperModel.openalex_id == paper.openalex_id)
            ).scalar_one_or_none()
            if result:
                return result

        # Fallback to title hash
        title_hash = paper.compute_title_hash()
        result = session.execute(
            select(PaperModel).where(PaperModel.title_hash == title_hash)
        ).scalar_one_or_none()
        return result

    def _create_model(self, paper: HarvestedPaper, now: datetime) -> PaperModel:
        """Create a new PaperModel from HarvestedPaper."""
        return PaperModel(
            doi=paper.doi,
            arxiv_id=paper.arxiv_id,
            semantic_scholar_id=paper.semantic_scholar_id,
            openalex_id=paper.openalex_id,
            title_hash=paper.compute_title_hash(),
            title=paper.title,
            abstract=paper.abstract,
            authors_json=json.dumps(paper.authors, ensure_ascii=False),
            year=paper.year,
            venue=paper.venue,
            publication_date=paper.publication_date,
            citation_count=paper.citation_count,
            url=paper.url,
            pdf_url=paper.pdf_url,
            keywords_json=json.dumps(paper.keywords, ensure_ascii=False),
            fields_of_study_json=json.dumps(paper.fields_of_study, ensure_ascii=False),
            primary_source=paper.source.value,
            sources_json=json.dumps([paper.source.value], ensure_ascii=False),
            created_at=now,
            updated_at=now,
        )

    def _update_paper(
        self, existing: PaperModel, paper: HarvestedPaper, now: datetime
    ) -> None:
        """Update existing paper with new data."""
        # Fill in missing identifiers
        if not existing.doi and paper.doi:
            existing.doi = paper.doi
        if not existing.arxiv_id and paper.arxiv_id:
            existing.arxiv_id = paper.arxiv_id
        if not existing.semantic_scholar_id and paper.semantic_scholar_id:
            existing.semantic_scholar_id = paper.semantic_scholar_id
        if not existing.openalex_id and paper.openalex_id:
            existing.openalex_id = paper.openalex_id

        # Prefer longer abstract
        if len(paper.abstract) > len(existing.abstract or ""):
            existing.abstract = paper.abstract

        # Prefer higher citation count
        if paper.citation_count > (existing.citation_count or 0):
            existing.citation_count = paper.citation_count

        # Fill in missing metadata
        if not existing.year and paper.year:
            existing.year = paper.year
        if not existing.venue and paper.venue:
            existing.venue = paper.venue
        if not existing.publication_date and paper.publication_date:
            existing.publication_date = paper.publication_date
        if not existing.url and paper.url:
            existing.url = paper.url
        if not existing.pdf_url and paper.pdf_url:
            existing.pdf_url = paper.pdf_url

        # Merge sources
        sources = existing.get_sources()
        if paper.source.value not in sources:
            sources.append(paper.source.value)
            existing.set_sources(sources)

        # Merge keywords and fields
        keywords = set(existing.get_keywords() + paper.keywords)
        existing.set_keywords(list(keywords))

        fields = set(existing.get_fields_of_study() + paper.fields_of_study)
        existing.set_fields_of_study(list(fields))

        existing.updated_at = now

    def search_papers(
        self,
        *,
        query: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        venues: Optional[List[str]] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        min_citations: Optional[int] = None,
        sources: Optional[List[str]] = None,
        sort_by: str = "citation_count",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[PaperModel], int]:
        """
        Search papers with filters and pagination.

        Returns:
            Tuple of (papers, total_count)
        """
        with self._provider.session() as session:
            stmt = select(PaperModel).where(PaperModel.deleted_at.is_(None))

            # Full-text search (LIKE for v1)
            if query:
                pattern = f"%{query}%"
                stmt = stmt.where(
                    or_(
                        PaperModel.title.ilike(pattern),
                        PaperModel.abstract.ilike(pattern),
                    )
                )

            # Year filters
            if year_from:
                stmt = stmt.where(PaperModel.year >= year_from)
            if year_to:
                stmt = stmt.where(PaperModel.year <= year_to)

            # Citation filter
            if min_citations:
                stmt = stmt.where(PaperModel.citation_count >= min_citations)

            # Venue filter
            if venues:
                venue_conditions = [PaperModel.venue.ilike(f"%{v}%") for v in venues]
                stmt = stmt.where(or_(*venue_conditions))

            # Source filter
            if sources:
                stmt = stmt.where(PaperModel.primary_source.in_(sources))

            # Count total before pagination
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total_count = session.execute(count_stmt).scalar() or 0

            # Sort
            sort_col = getattr(PaperModel, sort_by, PaperModel.citation_count)
            if sort_order.lower() == "desc":
                stmt = stmt.order_by(sort_col.desc())
            else:
                stmt = stmt.order_by(sort_col.asc())

            # Pagination
            stmt = stmt.offset(offset).limit(limit)

            papers = session.execute(stmt).scalars().all()

            return list(papers), total_count

    def get_paper_by_id(self, paper_id: int) -> Optional[PaperModel]:
        """Get a paper by its ID."""
        with self._provider.session() as session:
            return session.execute(
                select(PaperModel).where(
                    PaperModel.id == paper_id,
                    PaperModel.deleted_at.is_(None),
                )
            ).scalar_one_or_none()

    def get_user_library(
        self,
        user_id: str,
        *,
        track_id: Optional[int] = None,
        actions: Optional[List[str]] = None,
        sort_by: str = "saved_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[LibraryPaper], int]:
        """
        Get papers in user's library (saved papers).

        Joins papers table with paper_feedback where action in actions.
        """
        Logger.info("Starting to fetch user library", file=LogFiles.HARVEST)
        if actions is None:
            actions = ["save"]

        with self._provider.session() as session:
            # Join papers with feedback, then deduplicate by paper.id
            # paper_feedback.paper_id can be either:
            # 1. Integer ID as string (from harvest saves): "123" -> join on papers.id
            # 2. Semantic Scholar ID (from recommendation saves): "abc123" -> join on papers.semantic_scholar_id

            Logger.info("Executing database query to join papers with feedback", file=LogFiles.HARVEST)
            # First, get all matching paper-feedback pairs
            base_stmt = (
                select(PaperModel, PaperFeedbackModel)
                .join(
                    PaperFeedbackModel,
                    or_(
                        PaperModel.id == cast(PaperFeedbackModel.paper_id, Integer),
                        PaperModel.semantic_scholar_id == PaperFeedbackModel.paper_id,
                    ),
                )
                .where(
                    PaperFeedbackModel.user_id == user_id,
                    PaperFeedbackModel.action.in_(actions),
                    PaperModel.deleted_at.is_(None),
                )
            )

            if track_id is not None:
                base_stmt = base_stmt.where(PaperFeedbackModel.track_id == track_id)

            # Execute and deduplicate in Python by paper.id (keeping latest feedback)
            all_results = session.execute(base_stmt).all()
            Logger.info(f"Query returned {len(all_results)} results before deduplication", file=LogFiles.HARVEST)

            # Deduplicate by paper.id, keeping the one with latest timestamp
            Logger.info("Deduplicating results by paper id", file=LogFiles.HARVEST)
            paper_map: Dict[int, Tuple[PaperModel, PaperFeedbackModel]] = {}
            for row in all_results:
                paper = row[0]
                feedback = row[1]
                if paper.id not in paper_map or feedback.ts > paper_map[paper.id][1].ts:
                    paper_map[paper.id] = (paper, feedback)

            # Convert to list and sort
            unique_results = list(paper_map.values())
            Logger.info(f"After deduplication: {len(unique_results)} unique papers", file=LogFiles.HARVEST)

            # Sort
            min_ts = datetime.min.replace(tzinfo=timezone.utc)
            if sort_by == "saved_at":
                unique_results.sort(key=lambda x: x[1].ts or min_ts, reverse=(sort_order.lower() == "desc"))
            elif sort_by == "title":
                unique_results.sort(key=lambda x: x[0].title or "", reverse=(sort_order.lower() == "desc"))
            elif sort_by == "citation_count":
                unique_results.sort(key=lambda x: x[0].citation_count or 0, reverse=(sort_order.lower() == "desc"))
            elif sort_by == "year":
                unique_results.sort(key=lambda x: x[0].year or 0, reverse=(sort_order.lower() == "desc"))
            else:
                unique_results.sort(key=lambda x: x[1].ts or min_ts, reverse=(sort_order.lower() == "desc"))

            # Get total count before pagination
            total = len(unique_results)

            # Apply pagination
            paginated_results = unique_results[offset:offset + limit]

            return [
                LibraryPaper(
                    paper=row[0],
                    saved_at=row[1].ts,
                    track_id=row[1].track_id,
                    action=row[1].action,
                )
                for row in paginated_results
            ], total

    def remove_from_library(self, user_id: str, paper_id: int) -> bool:
        """Remove paper from user's library by deleting 'save' feedback."""
        with self._provider.session() as session:
            stmt = (
                PaperFeedbackModel.__table__.delete().where(
                    PaperFeedbackModel.user_id == user_id,
                    PaperFeedbackModel.paper_id == str(paper_id),
                    PaperFeedbackModel.action == "save",
                )
            )
            result = session.execute(stmt)
            session.commit()
            return result.rowcount > 0

    def create_harvest_run(
        self,
        run_id: str,
        keywords: List[str],
        venues: List[str],
        sources: List[str],
        max_results_per_source: int,
    ) -> HarvestRunModel:
        """Create a new harvest run record."""
        now = _utcnow()
        with self._provider.session() as session:
            run = HarvestRunModel(
                run_id=run_id,
                keywords_json=json.dumps(keywords, ensure_ascii=False),
                venues_json=json.dumps(venues, ensure_ascii=False),
                sources_json=json.dumps(sources, ensure_ascii=False),
                max_results_per_source=max_results_per_source,
                status="running",
                started_at=now,
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            return run

    def update_harvest_run(
        self,
        run_id: str,
        *,
        status: Optional[str] = None,
        papers_found: Optional[int] = None,
        papers_new: Optional[int] = None,
        papers_deduplicated: Optional[int] = None,
        errors: Optional[Dict[str, Any]] = None,
    ) -> Optional[HarvestRunModel]:
        """Update a harvest run record."""
        now = _utcnow()
        with self._provider.session() as session:
            run = session.execute(
                select(HarvestRunModel).where(HarvestRunModel.run_id == run_id)
            ).scalar_one_or_none()

            if run is None:
                return None

            if status is not None:
                run.status = status
                if status in ("success", "partial", "failed"):
                    run.ended_at = now

            if papers_found is not None:
                run.papers_found = papers_found
            if papers_new is not None:
                run.papers_new = papers_new
            if papers_deduplicated is not None:
                run.papers_deduplicated = papers_deduplicated
            if errors is not None:
                run.set_errors(errors)

            session.commit()
            session.refresh(run)
            return run

    def get_harvest_run(self, run_id: str) -> Optional[HarvestRunModel]:
        """Get a harvest run by its ID."""
        with self._provider.session() as session:
            return session.execute(
                select(HarvestRunModel).where(HarvestRunModel.run_id == run_id)
            ).scalar_one_or_none()

    def list_harvest_runs(
        self,
        *,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[HarvestRunModel]:
        """List harvest runs with optional filtering."""
        with self._provider.session() as session:
            stmt = select(HarvestRunModel)

            if status:
                stmt = stmt.where(HarvestRunModel.status == status)

            stmt = stmt.order_by(HarvestRunModel.started_at.desc())
            stmt = stmt.offset(offset).limit(limit)

            return list(session.execute(stmt).scalars().all())

    def get_paper_count(self) -> int:
        """Get total count of papers in the store."""
        with self._provider.session() as session:
            return (
                session.execute(
                    select(func.count()).select_from(PaperModel).where(
                        PaperModel.deleted_at.is_(None)
                    )
                ).scalar()
                or 0
            )

    def close(self) -> None:
        """Close database connections."""
        try:
            self._provider.engine.dispose()
        except Exception:
            pass


def paper_to_dict(paper: PaperModel) -> Dict[str, Any]:
    """Convert PaperModel to dictionary for API response."""
    return {
        "id": paper.id,
        "doi": paper.doi,
        "arxiv_id": paper.arxiv_id,
        "semantic_scholar_id": paper.semantic_scholar_id,
        "openalex_id": paper.openalex_id,
        "title": paper.title,
        "abstract": paper.abstract,
        "authors": paper.get_authors(),
        "year": paper.year,
        "venue": paper.venue,
        "publication_date": paper.publication_date,
        "citation_count": paper.citation_count,
        "url": paper.url,
        "pdf_url": paper.pdf_url,
        "keywords": paper.get_keywords(),
        "fields_of_study": paper.get_fields_of_study(),
        "primary_source": paper.primary_source,
        "sources": paper.get_sources(),
        "created_at": paper.created_at.isoformat() if paper.created_at else None,
        "updated_at": paper.updated_at.isoformat() if paper.updated_at else None,
    }
>>>>>>> 09ca42d (feat(Harvest): add -- Paper Search and Storage)
