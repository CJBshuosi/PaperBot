import pytest

from paperbot.application.workflows.topic_search_sources import (
    HFDailyTopicSource,
    TopicSearchSourceRegistry,
    dedupe_sources,
)


class _DummySource:
    name = "dummy"

    def search(self, *, query, branches, show_per_branch):
        return []


def test_topic_source_registry_register_create_available():
    registry = TopicSearchSourceRegistry()
    registry.register("dummy", _DummySource)

    assert registry.available() == ["dummy"]
    source = registry.create("dummy")
    assert source.name == "dummy"


def test_topic_source_registry_unknown_source():
    registry = TopicSearchSourceRegistry()
    with pytest.raises(KeyError):
        registry.create("missing")


def test_dedupe_sources_normalizes_case_and_blank():
    assert dedupe_sources([" papers_cool ", "PAPERS_COOL", "", "custom"]) == [
        "papers_cool",
        "custom",
    ]


def test_dedupe_sources_normalizes_hf_aliases():
    assert dedupe_sources(["huggingface_daily", "hf", "HF_DAILY"]) == ["hf_daily"]


class _FakeHFDailyConnector:
    def search(self, *, query, max_results, page_size=100, max_pages=5):
        return [
            type(
                "Row",
                (),
                {
                    "paper_id": "2602.12345",
                    "title": "KV Cache Compression",
                    "summary": "Fast KV cache pruning for long context.",
                    "published_at": "2026-02-10T00:00:00Z",
                    "submitted_on_daily_at": "2026-02-10T05:00:00Z",
                    "authors": ["Alice"],
                    "ai_keywords": ["kv", "cache"],
                    "upvotes": 9,
                    "paper_url": "https://huggingface.co/papers/2602.12345",
                    "external_url": "https://arxiv.org/abs/2602.12345",
                    "pdf_url": "https://arxiv.org/pdf/2602.12345.pdf",
                },
            )()
        ]


def test_hf_daily_topic_source_respects_branch_filter():
    source = HFDailyTopicSource(connector=_FakeHFDailyConnector())

    assert source.search(query="kv cache", branches=["venue"], show_per_branch=5) == []

    rows = source.search(query="kv cache", branches=["arxiv"], show_per_branch=5)
    assert len(rows) == 1
    assert rows[0].source == "hf_daily"
    assert rows[0].source_branch == "arxiv"
    assert rows[0].pdf_stars == 9
