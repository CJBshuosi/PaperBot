from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from paperbot.api import main as api_main
from paperbot.api.routes import research as research_route
from paperbot.infrastructure.stores.paper_store import SqlAlchemyPaperStore
from paperbot.infrastructure.stores.research_store import SqlAlchemyResearchStore


def _prepare_db(tmp_path: Path):
    db_path = tmp_path / "paper-routes.db"
    db_url = f"sqlite:///{db_path}"

    paper_store = SqlAlchemyPaperStore(db_url=db_url)
    research_store = SqlAlchemyResearchStore(db_url=db_url)

    paper = paper_store.upsert_paper(
        paper={
            "title": "UniICL",
            "url": "https://arxiv.org/abs/2501.12345",
            "pdf_url": "https://arxiv.org/pdf/2501.12345.pdf",
        }
    )
    track = research_store.create_track(user_id="u1", name="u1-track", activate=True)
    research_store.add_paper_feedback(
        user_id="u1",
        track_id=int(track["id"]),
        paper_id=str(paper["id"]),
        action="save",
        metadata={"title": "UniICL"},
    )
    research_store.ingest_repo_enrichment_rows(
        rows=[
            {
                "title": "UniICL",
                "paper_url": "https://arxiv.org/abs/2501.12345",
                "repo_url": "https://github.com/example/unicicl",
                "query": "icl compression",
                "github": {
                    "full_name": "example/unicicl",
                    "stars": 321,
                    "forks": 12,
                    "open_issues": 1,
                    "watchers": 18,
                    "language": "Python",
                    "license": "MIT",
                    "topics": ["icl", "llm"],
                    "html_url": "https://github.com/example/unicicl",
                },
            }
        ]
    )
    return research_store, int(paper["id"])


def test_saved_and_detail_routes(tmp_path, monkeypatch):
    store, paper_id = _prepare_db(tmp_path)
    monkeypatch.setattr(research_route, "_research_store", store)

    with TestClient(api_main.app) as client:
        saved = client.get("/api/research/papers/saved", params={"user_id": "u1"})
        detail = client.get(f"/api/research/papers/{paper_id}", params={"user_id": "u1"})

    assert saved.status_code == 200
    assert len(saved.json()["items"]) == 1

    assert detail.status_code == 200
    payload = detail.json()["detail"]
    assert payload["paper"]["id"] == paper_id
    assert payload["paper"]["title"] == "UniICL"
    assert len(payload["repos"]) == 1
    assert payload["repos"][0]["repo_url"] == "https://github.com/example/unicicl"


def test_update_status_route(tmp_path, monkeypatch):
    store, paper_id = _prepare_db(tmp_path)
    monkeypatch.setattr(research_route, "_research_store", store)

    with TestClient(api_main.app) as client:
        resp = client.post(
            f"/api/research/papers/{paper_id}/status",
            json={"user_id": "u1", "status": "reading", "mark_saved": True},
        )

    assert resp.status_code == 200
    payload = resp.json()["status"]
    assert payload["paper_id"] == paper_id
    assert payload["status"] == "reading"


def test_paper_repos_route(tmp_path, monkeypatch):
    store, paper_id = _prepare_db(tmp_path)
    monkeypatch.setattr(research_route, "_research_store", store)

    with TestClient(api_main.app) as client:
        resp = client.get(f"/api/research/papers/{paper_id}/repos")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["paper_id"] == str(paper_id)
    assert len(payload["repos"]) == 1
    assert payload["repos"][0]["full_name"] == "example/unicicl"
