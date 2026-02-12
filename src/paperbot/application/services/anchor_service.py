from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, desc, func, or_, select

from paperbot.infrastructure.stores.models import (
    AuthorModel,
    PaperAuthorModel,
    PaperFeedbackModel,
    PaperModel,
    ResearchTrackModel,
)
from paperbot.infrastructure.stores.sqlalchemy_db import SessionProvider, get_db_url


@dataclass
class _AuthorAggregate:
    author: AuthorModel
    paper_count: int
    citation_sum: int


def _parse_keywords(track: ResearchTrackModel) -> list[str]:
    try:
        rows = json.loads(track.keywords_json or "[]")
        if isinstance(rows, list):
            return [str(x).strip().lower() for x in rows if str(x).strip()]
    except Exception:
        pass
    return []


def _paper_text(paper: PaperModel) -> str:
    parts: list[str] = [paper.title or "", paper.abstract or ""]
    try:
        keywords = paper.get_keywords()
        if isinstance(keywords, list):
            parts.extend(str(x) for x in keywords)
    except Exception:
        pass
    return " ".join(parts).lower()


def _anchor_level(score: float) -> str:
    if score >= 0.75:
        return "core"
    if score >= 0.55:
        return "active"
    if score >= 0.35:
        return "emerging"
    return "background"


class AnchorService:
    """Discover anchor authors with intrinsic + track relevance scoring."""

    def __init__(self, db_url: Optional[str] = None):
        self._provider = SessionProvider(db_url or get_db_url())

    def discover(
        self,
        *,
        track_id: int,
        user_id: str = "default",
        limit: int = 20,
        window_years: int = 5,
    ) -> list[dict]:
        now_year = datetime.utcnow().year
        year_from = max(now_year - max(int(window_years), 1) + 1, 1970)

        with self._provider.session() as session:
            track = session.execute(
                select(ResearchTrackModel).where(ResearchTrackModel.id == int(track_id))
            ).scalar_one_or_none()
            if track is None:
                raise ValueError(f"track not found: {track_id}")
            keywords = _parse_keywords(track)

            rows = session.execute(
                select(
                    AuthorModel,
                    func.count(PaperAuthorModel.paper_id).label("paper_count"),
                    func.sum(func.coalesce(PaperModel.citation_count, 0)).label("citation_sum"),
                )
                .join(PaperAuthorModel, PaperAuthorModel.author_id == AuthorModel.id)
                .join(PaperModel, PaperModel.id == PaperAuthorModel.paper_id)
                .where(
                    or_(
                        PaperModel.year.is_(None),
                        and_(PaperModel.year >= year_from, PaperModel.year <= now_year),
                    )
                )
                .group_by(AuthorModel.id)
                .order_by(desc("citation_sum"), desc("paper_count"))
                .limit(max(int(limit), 1) * 4)
            ).all()

            aggregates: list[_AuthorAggregate] = []
            for author, paper_count, citation_sum in rows:
                aggregates.append(
                    _AuthorAggregate(
                        author=author,
                        paper_count=max(int(paper_count or 0), 0),
                        citation_sum=max(int(citation_sum or 0), 0),
                    )
                )

            if not aggregates:
                return []

            max_paper_count = max(x.paper_count for x in aggregates) or 1
            max_citation_sum = max(x.citation_sum for x in aggregates) or 1

            payload: list[dict] = []
            for item in aggregates:
                author_papers = (
                    session.execute(
                        select(PaperModel)
                        .join(PaperAuthorModel, PaperAuthorModel.paper_id == PaperModel.id)
                        .where(PaperAuthorModel.author_id == item.author.id)
                        .where(
                            or_(
                                PaperModel.year.is_(None),
                                and_(PaperModel.year >= year_from, PaperModel.year <= now_year),
                            )
                        )
                        .order_by(PaperModel.citation_count.desc(), PaperModel.id.desc())
                        .limit(25)
                    )
                    .scalars()
                    .all()
                )
                if not author_papers:
                    continue

                keyword_matches = []
                if keywords:
                    for paper in author_papers:
                        text = _paper_text(paper)
                        if any(k in text for k in keywords):
                            keyword_matches.append(paper)

                paper_ids = [int(p.id) for p in author_papers if p.id is not None]
                feedback_rows = []
                if paper_ids:
                    feedback_rows = (
                        session.execute(
                            select(PaperFeedbackModel)
                            .where(PaperFeedbackModel.track_id == int(track_id))
                            .where(PaperFeedbackModel.user_id == user_id)
                            .where(
                                or_(
                                    PaperFeedbackModel.canonical_paper_id.in_(paper_ids),
                                    PaperFeedbackModel.paper_ref_id.in_(paper_ids),
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )

                paper_volume_score = float(item.paper_count) / float(max_paper_count)
                citation_score = float(item.citation_sum) / float(max_citation_sum)
                intrinsic_score = 0.5 * paper_volume_score + 0.5 * citation_score

                keyword_match_rate = (
                    float(len(keyword_matches)) / float(len(author_papers))
                    if author_papers
                    else 0.0
                )

                action_weights = {
                    "like": 1.0,
                    "save": 1.0,
                    "cite": 1.2,
                    "dislike": -1.0,
                    "skip": -0.3,
                }
                raw_feedback = 0.0
                for row in feedback_rows:
                    raw_feedback += action_weights.get((row.action or "").lower(), 0.0)
                feedback_signal = (
                    (math.tanh(raw_feedback / 4.0) + 1.0) / 2.0 if feedback_rows else 0.0
                )

                relevance_score = 0.7 * keyword_match_rate + 0.3 * feedback_signal
                anchor_score = 0.6 * intrinsic_score + 0.4 * relevance_score
                level = _anchor_level(anchor_score)

                item.author.anchor_score = float(round(anchor_score, 6))
                item.author.anchor_level = level
                item.author.paper_count = item.paper_count
                item.author.citation_count = item.citation_sum

                evidence = (keyword_matches or author_papers)[:3]
                evidence_rows = [
                    {
                        "paper_id": int(p.id),
                        "title": p.title,
                        "year": p.year,
                        "url": p.url,
                        "citation_count": int(p.citation_count or 0),
                    }
                    for p in evidence
                ]

                payload.append(
                    {
                        "author_id": int(item.author.id),
                        "author_ref": item.author.author_id,
                        "name": item.author.name,
                        "slug": item.author.slug,
                        "anchor_score": float(round(anchor_score, 4)),
                        "anchor_level": level,
                        "intrinsic_score": float(round(intrinsic_score, 4)),
                        "relevance_score": float(round(relevance_score, 4)),
                        "paper_count": int(item.paper_count),
                        "citation_sum": int(item.citation_sum),
                        "keyword_match_rate": float(round(keyword_match_rate, 4)),
                        "feedback_signal": float(round(feedback_signal, 4)),
                        "evidence_papers": evidence_rows,
                    }
                )

            session.commit()

        payload.sort(
            key=lambda row: (row["anchor_score"], row["relevance_score"], row["paper_count"]),
            reverse=True,
        )
        return payload[: max(int(limit), 1)]
