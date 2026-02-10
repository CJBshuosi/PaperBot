from fastapi.testclient import TestClient

from paperbot.api import main as api_main
from paperbot.api.routes import research as research_route


class _FakeSemanticScholarClient:
    def __init__(self, api_key=None):
        self.api_key = api_key

    async def get_author(self, author_id, fields=None):
        return {
            "authorId": author_id,
            "name": "Alice",
            "affiliations": ["Lab"],
            "paperCount": 10,
            "citationCount": 100,
            "hIndex": 12,
        }

    async def get_author_papers(self, author_id, limit=100, fields=None):
        return [
            {
                "title": "Paper A",
                "year": 2025,
                "citationCount": 10,
                "venue": "NeurIPS",
                "fieldsOfStudy": ["Machine Learning"],
                "authors": [
                    {"authorId": author_id, "name": "Alice"},
                    {"authorId": "c1", "name": "Bob"},
                ],
            },
            {
                "title": "Paper B",
                "year": 2024,
                "citationCount": 4,
                "venue": "ICLR",
                "fieldsOfStudy": ["Machine Learning", "Optimization"],
                "authors": [
                    {"authorId": author_id, "name": "Alice"},
                    {"authorId": "c1", "name": "Bob"},
                    {"authorId": "c2", "name": "Carol"},
                ],
            },
        ]

    async def close(self):
        return None


def test_scholar_network_route(monkeypatch):
    monkeypatch.setattr(research_route, "SemanticScholarClient", _FakeSemanticScholarClient)

    with TestClient(api_main.app) as client:
        resp = client.post(
            "/api/research/scholar/network",
            json={
                "scholar_id": "s1",
                "max_papers": 20,
                "recent_years": 10,
                "max_nodes": 10,
            },
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["scholar"]["name"] == "Alice"
    assert payload["stats"]["coauthor_count"] == 2
    assert len(payload["edges"]) == 2


def test_scholar_trends_route(monkeypatch):
    monkeypatch.setattr(research_route, "SemanticScholarClient", _FakeSemanticScholarClient)

    with TestClient(api_main.app) as client:
        resp = client.post(
            "/api/research/scholar/trends",
            json={
                "scholar_id": "s1",
                "max_papers": 20,
                "year_window": 10,
            },
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["scholar"]["name"] == "Alice"
    assert len(payload["publication_velocity"]) >= 1
    assert payload["trend_summary"]["publication_trend"] in {"up", "down", "flat"}
