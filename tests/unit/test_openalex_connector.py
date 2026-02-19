from __future__ import annotations

from paperbot.infrastructure.connectors.openalex_connector import OpenAlexConnector


class _DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


def test_resolve_work_by_doi(monkeypatch):
    calls = []

    def _fake_get(url, headers, params=None, timeout=0):
        calls.append({"url": url, "params": params})
        if url.endswith("/works"):
            return _DummyResponse({"results": [{"id": "https://openalex.org/W123", "title": "A"}]})
        return _DummyResponse({})

    monkeypatch.setattr(
        "paperbot.infrastructure.connectors.openalex_connector.requests.get", _fake_get
    )

    connector = OpenAlexConnector()
    row = connector.resolve_work(seed_type="doi", seed_id="10.1000/xyz.1")
    assert row is not None
    assert row["id"] == "https://openalex.org/W123"
    assert calls[0]["params"]["filter"].startswith("doi:")


def test_related_and_references_load_by_id(monkeypatch):
    rows = {
        "W1": {
            "id": "https://openalex.org/W1",
            "title": "Seed",
            "related_works": ["https://openalex.org/W2"],
            "referenced_works": ["https://openalex.org/W3"],
        },
        "W2": {"id": "https://openalex.org/W2", "title": "Related"},
        "W3": {"id": "https://openalex.org/W3", "title": "Ref"},
    }

    def _fake_get(url, headers, params=None, timeout=0):
        key = url.split("/")[-1]
        if key in rows:
            return _DummyResponse(rows[key])
        return _DummyResponse({})

    monkeypatch.setattr(
        "paperbot.infrastructure.connectors.openalex_connector.requests.get", _fake_get
    )

    connector = OpenAlexConnector()
    seed = connector.get_work("W1")
    assert seed is not None
    related = connector.get_related_works(seed, limit=5)
    refs = connector.get_referenced_works(seed, limit=5)
    assert len(related) == 1
    assert len(refs) == 1
    assert related[0]["title"] == "Related"
    assert refs[0]["title"] == "Ref"


def test_get_citing_works(monkeypatch):
    def _fake_get(url, headers, params=None, timeout=0):
        if "cited-by" in url:
            return _DummyResponse(
                {"results": [{"id": "https://openalex.org/W9", "title": "Citing"}]}
            )
        return _DummyResponse({})

    monkeypatch.setattr(
        "paperbot.infrastructure.connectors.openalex_connector.requests.get", _fake_get
    )
    connector = OpenAlexConnector()
    rows = connector.get_citing_works(
        {"cited_by_api_url": "https://api.openalex.org/works?filter=cited-by:W1"}, limit=10
    )
    assert len(rows) == 1
    assert rows[0]["title"] == "Citing"
