from __future__ import annotations

from paperbot.infrastructure.connectors.zotero_connector import ZoteroConnector


class _DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


def test_zotero_item_to_paper_mapping():
    item = {
        "key": "ABCD1234",
        "data": {
            "title": "Scaling Laws for LMs",
            "creators": [
                {"creatorType": "author", "firstName": "Alice", "lastName": "Smith"},
                {"creatorType": "author", "name": "Bob Doe"},
            ],
            "date": "2024-03-01",
            "publicationTitle": "NeurIPS",
            "DOI": "https://doi.org/10.1000/xyz.123",
            "url": "https://arxiv.org/abs/2401.01234",
            "abstractNote": "Test abstract",
        },
    }

    paper = ZoteroConnector.zotero_item_to_paper(item)
    assert paper["title"] == "Scaling Laws for LMs"
    assert paper["authors"] == ["Alice Smith", "Bob Doe"]
    assert paper["year"] == 2024
    assert paper["venue"] == "NeurIPS"
    assert paper["doi"] == "10.1000/xyz.123"
    assert paper["arxiv_id"] == "2401.01234"
    assert paper["zotero_key"] == "ABCD1234"


def test_paper_to_zotero_item_mapping():
    paper = {
        "title": "Fast Retrieval",
        "authors": ["Jane Doe", "John Smith"],
        "year": 2025,
        "venue": "ICLR",
        "abstract": "A",
        "doi": "10.1000/abc.8",
        "url": "https://example.com/paper",
        "arxiv_id": "2502.01234",
    }
    item = ZoteroConnector.paper_to_zotero_item(paper)
    assert item["itemType"] == "journalArticle"
    assert item["title"] == "Fast Retrieval"
    assert item["date"] == "2025"
    assert item["publicationTitle"] == "ICLR"
    assert item["DOI"] == "10.1000/abc.8"
    assert item["archiveLocation"] == "2502.01234"
    assert len(item["creators"]) == 2


def test_dedupe_keys_prefer_doi_then_arxiv_then_url():
    with_doi = {"doi": "10.1000/abc.9", "arxiv_id": "2501.00001", "url": "https://x"}
    with_arxiv = {"arxiv_id": "2501.00001", "url": "https://x"}
    with_url = {"url": "https://example.com/a"}
    with_title = {"title": "  My Paper  ", "year": 2024}

    assert ZoteroConnector.paper_dedupe_key(with_doi) == "doi:10.1000/abc.9"
    assert ZoteroConnector.paper_dedupe_key(with_arxiv) == "arxiv:2501.00001"
    assert ZoteroConnector.paper_dedupe_key(with_url) == "url:https://example.com/a"
    assert ZoteroConnector.paper_dedupe_key(with_title) == "title:my paper|2024"


def test_list_all_items_paginates(monkeypatch):
    pages = [
        [{"key": str(i)} for i in range(100)],
        [{"key": str(i)} for i in range(100, 150)],
    ]
    calls = []

    def _fake_get(url, headers, params, timeout):
        calls.append({"url": url, "params": dict(params), "timeout": timeout})
        index = int(params.get("start", 0)) // 100
        payload = pages[index] if index < len(pages) else []
        return _DummyResponse(payload)

    monkeypatch.setattr(
        "paperbot.infrastructure.connectors.zotero_connector.requests.get", _fake_get
    )

    connector = ZoteroConnector()
    rows = connector.list_all_items(
        api_key="k",
        library_type="user",
        library_id="123",
        max_items=150,
    )
    assert len(rows) == 150
    assert calls[0]["params"]["start"] == 0
    assert calls[1]["params"]["start"] == 100


def test_create_items_posts_payload(monkeypatch):
    posted = {}

    def _fake_post(url, headers, json, timeout):
        posted["url"] = url
        posted["headers"] = headers
        posted["json"] = json
        posted["timeout"] = timeout
        return _DummyResponse({"successful": {"0": "OK"}})

    monkeypatch.setattr(
        "paperbot.infrastructure.connectors.zotero_connector.requests.post", _fake_post
    )

    connector = ZoteroConnector()
    payload = connector.create_items(
        api_key="k",
        library_type="group",
        library_id="456",
        items=[{"title": "A"}],
    )
    assert payload["successful"] == {"0": "OK"}
    assert posted["url"].endswith("/groups/456/items")
