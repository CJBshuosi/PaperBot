from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import desc, func, select

from paperbot.domain.paper_identity import normalize_arxiv_id, normalize_doi
from paperbot.infrastructure.stores.models import Base, PaperJudgeScoreModel, PaperModel
from paperbot.infrastructure.stores.sqlalchemy_db import SessionProvider, get_db_url


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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

    def __init__(self, db_url: Optional[str] = None, *, auto_create_schema: bool = True):
        self.db_url = db_url or get_db_url()
        self._provider = SessionProvider(self.db_url)
        if auto_create_schema:
            Base.metadata.create_all(self._provider.engine)

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
