from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from paperbot.api import main as api_main
from paperbot.api.routes import research as research_route
from paperbot.application.services.anchor_service import AnchorService
from paperbot.infrastructure.stores.author_store import AuthorStore
from paperbot.infrastructure.stores.models import Base, ResearchTrackModel
from paperbot.infrastructure.stores.paper_store import PaperStore
from paperbot.infrastructure.stores.research_store import SqlAlchemyResearchStore
from paperbot.infrastructure.stores.sqlalchemy_db import SessionProvider
from paperbot.infrastructure.stores.workflow_metric_store import WorkflowMetricStore


def test_anchor_action_set_and_list_routes(tmp_path: Path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'anchor-action-route.db'}"
    provider = SessionProvider(db_url)
    Base.metadata.create_all(provider.engine)

    with provider.session() as session:
        track = ResearchTrackModel(
            user_id="u-anchor",
            name="LLM",
            description="",
            keywords_json=json.dumps(["attention"]),
            venues_json="[]",
            methods_json="[]",
            is_active=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(track)
        session.commit()
        session.refresh(track)
        track_id = int(track.id)

    paper = PaperStore(db_url=db_url).upsert_paper(
        paper={
            "title": "Attention Is All You Need",
            "paper_id": "1706.03762",
            "url": "https://arxiv.org/abs/1706.03762",
            "authors": ["Alice Smith"],
            "year": 2017,
        },
        source_hint="arxiv",
    )
    AuthorStore(db_url=db_url).replace_paper_authors(
        paper_id=int(paper["id"]), authors=["Alice Smith"]
    )

    research_store = SqlAlchemyResearchStore(db_url=db_url)
    anchor_service = AnchorService(db_url=db_url)
    metric_store = WorkflowMetricStore(db_url=db_url)

    monkeypatch.setattr(research_route, "_research_store", research_store)
    monkeypatch.setattr(research_route, "_anchor_service", anchor_service)
    monkeypatch.setattr(research_route, "_workflow_metric_store", metric_store)

    with TestClient(api_main.app) as client:
        set_resp = client.post(
            f"/api/research/tracks/{track_id}/anchors/1/action",
            json={"user_id": "u-anchor", "action": "follow"},
        )
        list_resp = client.get(
            f"/api/research/tracks/{track_id}/anchors/actions",
            params={"user_id": "u-anchor"},
        )

    assert set_resp.status_code == 200
    payload = set_resp.json()["action"]
    assert payload["user_id"] == "u-anchor"
    assert payload["track_id"] == track_id
    assert payload["author_id"] == 1
    assert payload["action"] == "follow"

    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["action"] == "follow"

    summary = metric_store.summarize(days=1, workflow="anchor_action", track_id=track_id)
    assert summary["totals"]["runs"] >= 1


def test_anchor_action_rejects_invalid_action(tmp_path: Path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'anchor-action-invalid.db'}"
    provider = SessionProvider(db_url)
    Base.metadata.create_all(provider.engine)

    with provider.session() as session:
        track = ResearchTrackModel(
            user_id="u-anchor",
            name="LLM",
            description="",
            keywords_json=json.dumps(["attention"]),
            venues_json="[]",
            methods_json="[]",
            is_active=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(track)
        session.commit()
        session.refresh(track)
        track_id = int(track.id)

    research_store = SqlAlchemyResearchStore(db_url=db_url)
    monkeypatch.setattr(research_route, "_research_store", research_store)
    monkeypatch.setattr(research_route, "_anchor_service", AnchorService(db_url=db_url))

    with TestClient(api_main.app) as client:
        resp = client.post(
            f"/api/research/tracks/{track_id}/anchors/999/action",
            json={"user_id": "u-anchor", "action": "invalid"},
        )

    # request model validation happens before handler.
    assert resp.status_code == 422


def test_anchor_routes_respect_feature_flag(tmp_path: Path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'anchor-flag.db'}"
    store = SqlAlchemyResearchStore(db_url=db_url)
    track = store.create_track(
        user_id="u-anchor", name="LLM", keywords=["attention"], activate=True
    )

    monkeypatch.setattr(research_route, "_research_store", store)
    monkeypatch.setattr(research_route, "_anchor_service", AnchorService(db_url=db_url))
    monkeypatch.setattr(research_route, "ENABLE_ANCHOR_AUTHORS", False)

    with TestClient(api_main.app) as client:
        resp = client.get(
            f"/api/research/tracks/{int(track['id'])}/anchors/discover",
            params={"user_id": "u-anchor"},
        )

    assert resp.status_code == 503
    assert "PAPERBOT_ENABLE_ANCHOR_AUTHORS" in resp.json()["detail"]
