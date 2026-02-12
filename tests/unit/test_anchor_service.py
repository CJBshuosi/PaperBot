from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from paperbot.application.services.anchor_service import AnchorService
from paperbot.infrastructure.stores.author_store import AuthorStore
from paperbot.infrastructure.stores.models import Base, PaperFeedbackModel, ResearchTrackModel
from paperbot.infrastructure.stores.paper_store import PaperStore
from paperbot.infrastructure.stores.sqlalchemy_db import SessionProvider


def _seed_track(db_url: str) -> int:
    provider = SessionProvider(db_url)
    Base.metadata.create_all(provider.engine)
    with provider.session() as session:
        track = ResearchTrackModel(
            user_id="default",
            name="LLM Systems",
            description="",
            keywords_json=json.dumps(["attention", "transformer"]),
            venues_json="[]",
            methods_json="[]",
            is_active=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(track)
        session.commit()
        session.refresh(track)
        return int(track.id)


def test_anchor_service_discovers_and_scores_authors(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / 'anchor-service.db'}"
    paper_store = PaperStore(db_url=db_url)
    author_store = AuthorStore(db_url=db_url)
    provider = SessionProvider(db_url)

    track_id = _seed_track(db_url)

    p1 = paper_store.upsert_paper(
        paper={
            "title": "Attention Is All You Need",
            "abstract": "Transformer architecture for sequence modeling.",
            "paper_id": "1706.03762",
            "url": "https://arxiv.org/abs/1706.03762",
            "year": 2017,
            "citation_count": 5000,
            "authors": ["Alice Smith"],
        },
        source_hint="arxiv",
    )
    p2 = paper_store.upsert_paper(
        paper={
            "title": "Scaling Transformer Inference",
            "abstract": "Efficient attention serving system.",
            "paper_id": "2401.00011",
            "url": "https://arxiv.org/abs/2401.00011",
            "year": 2025,
            "citation_count": 120,
            "authors": ["Alice Smith"],
        },
        source_hint="arxiv",
    )
    p3 = paper_store.upsert_paper(
        paper={
            "title": "Database Joins for HTAP",
            "abstract": "Index design for mixed workloads.",
            "paper_id": "2401.00022",
            "url": "https://arxiv.org/abs/2401.00022",
            "year": 2025,
            "citation_count": 900,
            "authors": ["Bob Lee"],
        },
        source_hint="arxiv",
    )

    author_store.replace_paper_authors(paper_id=int(p1["id"]), authors=["Alice Smith"])
    author_store.replace_paper_authors(paper_id=int(p2["id"]), authors=["Alice Smith"])
    author_store.replace_paper_authors(paper_id=int(p3["id"]), authors=["Bob Lee"])

    with provider.session() as session:
        session.add(
            PaperFeedbackModel(
                user_id="default",
                track_id=track_id,
                paper_id=str(p2["id"]),
                paper_ref_id=int(p2["id"]),
                canonical_paper_id=int(p2["id"]),
                action="like",
                weight=1.0,
                ts=datetime.now(timezone.utc),
                metadata_json="{}",
            )
        )
        session.commit()

    service = AnchorService(db_url=db_url)
    anchors = service.discover(track_id=track_id, user_id="default", limit=5, window_years=15)

    assert len(anchors) >= 2
    assert anchors[0]["name"] == "Alice Smith"
    assert anchors[0]["anchor_level"] in {"core", "active", "emerging"}
    assert anchors[0]["anchor_score"] >= anchors[1]["anchor_score"]
    assert anchors[0]["relevance_score"] > 0
    assert anchors[0]["evidence_papers"]


def test_anchor_service_raises_for_unknown_track(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / 'anchor-track-missing.db'}"
    service = AnchorService(db_url=db_url)
    with pytest.raises(ValueError, match="track not found"):
        service.discover(track_id=999, user_id="default")
