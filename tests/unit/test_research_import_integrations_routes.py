from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from paperbot.api import main as api_main
from paperbot.api.routes import research as research_route
from paperbot.infrastructure.stores.paper_store import SqlAlchemyPaperStore
from paperbot.infrastructure.stores.research_store import SqlAlchemyResearchStore


def _prepare_stores(tmp_path: Path):
    db_path = tmp_path / "research-imports.db"
    db_url = f"sqlite:///{db_path}"
    research_store = SqlAlchemyResearchStore(db_url=db_url)
    paper_store = SqlAlchemyPaperStore(db_url=db_url)
    return research_store, paper_store


def test_bibtex_import_route_creates_track_and_saves(tmp_path, monkeypatch):
    research_store, paper_store = _prepare_stores(tmp_path)
    monkeypatch.setattr(research_route, "_research_store", research_store)
    monkeypatch.setattr(research_route, "_paper_store", paper_store)

    blob = """
@article{vaswani2017,
  title = {Attention Is All You Need},
  author = {Vaswani, Ashish and Shazeer, Noam},
  year = {2017},
  doi = {10.5555/3295222.3295349},
  url = {https://arxiv.org/abs/1706.03762}
}
"""

    with TestClient(api_main.app) as client:
        resp = client.post(
            "/api/research/papers/import/bibtex",
            json={"user_id": "u-import", "content": blob, "track_name": "RR Import"},
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["parsed"] == 1
    assert payload["imported"] == 1
    assert payload["created"] == 1
    assert payload["track_name"] == "RR Import"

    saved = research_store.list_saved_papers(user_id="u-import", track_id=payload["track_id"])
    assert len(saved) == 1
    assert saved[0]["paper"]["title"] == "Attention Is All You Need"


def test_zotero_pull_route_imports_and_saves(tmp_path, monkeypatch):
    research_store, paper_store = _prepare_stores(tmp_path)
    monkeypatch.setattr(research_route, "_research_store", research_store)
    monkeypatch.setattr(research_route, "_paper_store", paper_store)

    class _FakeConnector:
        def list_all_items(self, **kwargs):
            return [
                {
                    "key": "ABCD",
                    "data": {
                        "title": "A Pulled Paper",
                        "creators": [{"creatorType": "author", "name": "Alice"}],
                        "date": "2025",
                        "publicationTitle": "ICLR",
                        "DOI": "10.1000/pulled.1",
                    },
                }
            ]

        @staticmethod
        def zotero_item_to_paper(item):
            return {
                "title": item["data"]["title"],
                "authors": ["Alice"],
                "year": 2025,
                "venue": "ICLR",
                "doi": "10.1000/pulled.1",
                "source": "zotero",
                "primary_source": "zotero",
            }

    monkeypatch.setattr(
        "paperbot.infrastructure.connectors.zotero_connector.ZoteroConnector",
        _FakeConnector,
    )

    with TestClient(api_main.app) as client:
        resp = client.post(
            "/api/research/integrations/zotero/pull",
            json={
                "user_id": "u-zotero",
                "track_name": "Zotero Import",
                "library_type": "user",
                "library_id": "1",
                "api_key": "k",
                "max_items": 10,
            },
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["imported"] == 1
    assert payload["created"] == 1

    saved = research_store.list_saved_papers(user_id="u-zotero", track_id=payload["track_id"])
    assert len(saved) == 1
    assert saved[0]["paper"]["title"] == "A Pulled Paper"


def test_zotero_push_route_pushes_non_duplicate_saved_papers(tmp_path, monkeypatch):
    research_store, paper_store = _prepare_stores(tmp_path)
    monkeypatch.setattr(research_route, "_research_store", research_store)
    monkeypatch.setattr(research_route, "_paper_store", paper_store)

    track = research_store.create_track(user_id="u-push", name="Push Track", activate=True)
    paper = paper_store.upsert_paper(
        paper={
            "title": "Paper To Push",
            "authors": ["Jane Doe"],
            "year": 2026,
            "doi": "10.1000/push.1",
            "url": "https://example.com/push",
        }
    )
    research_store.add_paper_feedback(
        user_id="u-push",
        track_id=int(track["id"]),
        paper_id=str(paper["id"]),
        action="save",
        metadata={},
    )

    class _FakeConnector:
        def __init__(self):
            self.sent = []

        def list_all_items(self, **kwargs):
            return []

        @staticmethod
        def item_dedupe_key(item):
            return None

        @staticmethod
        def paper_dedupe_key(paper):
            return f"doi:{paper.get('doi')}"

        @staticmethod
        def paper_to_zotero_item(paper):
            return {"title": paper.get("title")}

        def create_items(self, **kwargs):
            items = kwargs.get("items") or []
            self.sent.extend(items)
            return {"successful": {str(idx): "ok" for idx, _ in enumerate(items)}}

    monkeypatch.setattr(
        "paperbot.infrastructure.connectors.zotero_connector.ZoteroConnector",
        _FakeConnector,
    )

    with TestClient(api_main.app) as client:
        resp = client.post(
            "/api/research/integrations/zotero/push",
            json={
                "user_id": "u-push",
                "track_id": int(track["id"]),
                "library_type": "user",
                "library_id": "9",
                "api_key": "k",
                "max_items": 10,
                "dry_run": False,
            },
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["local_saved"] == 1
    assert payload["to_push"] == 1
    assert payload["pushed"] == 1
