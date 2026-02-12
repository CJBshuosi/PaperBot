from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from paperbot.api import main as api_main
from paperbot.api.routes import research as research_route
from paperbot.infrastructure.stores.research_store import SqlAlchemyResearchStore


class _FakeAnchorService:
    def discover(
        self,
        *,
        track_id: int,
        user_id: str,
        limit: int,
        window_years: int,
        personalized: bool,
    ):
        return [
            {
                "author_id": 1,
                "author_ref": "name:alice-smith",
                "name": "Alice Smith",
                "slug": "alice-smith",
                "anchor_score": 0.88,
                "anchor_level": "core",
                "intrinsic_score": 0.91,
                "relevance_score": 0.83,
                "paper_count": 12,
                "citation_sum": 3210,
                "keyword_match_rate": 0.8,
                "feedback_signal": 0.7,
                "evidence_papers": [
                    {
                        "paper_id": 101,
                        "title": "Attention Is All You Need",
                        "year": 2017,
                        "url": "https://arxiv.org/abs/1706.03762",
                        "citation_count": 5000,
                    }
                ],
                "_meta": {
                    "track_id": track_id,
                    "user_id": user_id,
                    "limit": limit,
                    "window_years": window_years,
                    "personalized": personalized,
                },
            }
        ]


class _ErrorAnchorService:
    def discover(
        self,
        *,
        track_id: int,
        user_id: str,
        limit: int,
        window_years: int,
        personalized: bool,
    ):
        raise ValueError("track not found: 999")


def test_anchor_discover_route_returns_items(tmp_path: Path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'anchor-discover-route.db'}"
    store = SqlAlchemyResearchStore(db_url=db_url)
    track = store.create_track(
        user_id="u-anchor", name="LLM", keywords=["transformer"], activate=True
    )

    monkeypatch.setattr(research_route, "_research_store", store)
    monkeypatch.setattr(research_route, "_anchor_service", _FakeAnchorService())

    with TestClient(api_main.app) as client:
        resp = client.get(
            f"/api/research/tracks/{int(track['id'])}/anchors/discover",
            params={"user_id": "u-anchor", "limit": 5, "window_days": 730},
        )
        resp_global = client.get(
            f"/api/research/tracks/{int(track['id'])}/anchors/discover",
            params={
                "user_id": "u-anchor",
                "limit": 5,
                "window_days": 730,
                "personalized": "false",
            },
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["track_id"] == int(track["id"])
    assert payload["window_days"] == 730
    assert payload["limit"] == 5
    assert payload["personalized"] is True
    assert len(payload["items"]) == 1
    assert payload["items"][0]["name"] == "Alice Smith"
    assert payload["items"][0]["_meta"]["window_years"] == 2
    assert payload["items"][0]["_meta"]["personalized"] is True

    assert resp_global.status_code == 200
    payload_global = resp_global.json()
    assert payload_global["personalized"] is False
    assert payload_global["items"][0]["_meta"]["personalized"] is False


def test_anchor_discover_route_returns_404_for_missing_track(tmp_path: Path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'anchor-discover-track-missing.db'}"
    store = SqlAlchemyResearchStore(db_url=db_url)

    monkeypatch.setattr(research_route, "_research_store", store)
    monkeypatch.setattr(research_route, "_anchor_service", _FakeAnchorService())

    with TestClient(api_main.app) as client:
        resp = client.get(
            "/api/research/tracks/999/anchors/discover",
            params={"user_id": "u-anchor"},
        )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Track not found"


def test_anchor_discover_route_maps_service_value_error(tmp_path: Path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'anchor-discover-error.db'}"
    store = SqlAlchemyResearchStore(db_url=db_url)
    track = store.create_track(
        user_id="u-anchor", name="LLM", keywords=["transformer"], activate=True
    )

    monkeypatch.setattr(research_route, "_research_store", store)
    monkeypatch.setattr(research_route, "_anchor_service", _ErrorAnchorService())

    with TestClient(api_main.app) as client:
        resp = client.get(
            f"/api/research/tracks/{int(track['id'])}/anchors/discover",
            params={"user_id": "u-anchor"},
        )

    assert resp.status_code == 404
    assert "track not found" in resp.json()["detail"]
