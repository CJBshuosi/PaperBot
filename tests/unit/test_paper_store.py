from __future__ import annotations

from pathlib import Path

from paperbot.application.workflows.dailypaper import (
    build_daily_paper_report,
    ingest_daily_report_to_registry,
)
from paperbot.infrastructure.stores.paper_store import SqlAlchemyPaperStore


def _sample_search_result():
    return {
        "source": "papers.cool",
        "sources": ["papers_cool", "arxiv_api"],
        "queries": [
            {
                "raw_query": "ICL压缩",
                "normalized_query": "icl compression",
                "total_hits": 1,
                "items": [
                    {
                        "title": "UniICL",
                        "url": "https://arxiv.org/abs/2501.12345",
                        "external_url": "https://arxiv.org/abs/2501.12345",
                        "pdf_url": "https://arxiv.org/pdf/2501.12345.pdf",
                        "score": 10.2,
                        "snippet": "compress in-context learning",
                        "authors": ["A", "B"],
                        "keywords": ["icl", "compression"],
                        "matched_queries": ["icl compression"],
                    }
                ],
            }
        ],
        "items": [
            {
                "title": "UniICL",
                "url": "https://arxiv.org/abs/2501.12345",
                "external_url": "https://arxiv.org/abs/2501.12345",
                "pdf_url": "https://arxiv.org/pdf/2501.12345.pdf",
                "score": 10.2,
                "snippet": "compress in-context learning",
                "authors": ["A", "B"],
                "keywords": ["icl", "compression"],
                "matched_queries": ["icl compression"],
            }
        ],
        "summary": {
            "unique_items": 1,
            "total_query_hits": 1,
        },
    }


def test_ingest_daily_report_to_registry_is_idempotent(tmp_path: Path):
    db_path = tmp_path / "paper-registry.db"
    store = SqlAlchemyPaperStore(db_url=f"sqlite:///{db_path}")

    report = build_daily_paper_report(search_result=_sample_search_result(), title="Daily", top_n=5)

    first = ingest_daily_report_to_registry(report, paper_store=store)
    second = ingest_daily_report_to_registry(report, paper_store=store)

    assert first["total"] == 1
    assert first["created"] == 1
    assert first["updated"] == 0

    assert second["total"] == 1
    assert second["created"] == 0
    assert second["updated"] == 1

    rows = store.list_recent(limit=5)
    assert len(rows) == 1
    assert rows[0]["arxiv_id"] == "2501.12345"
    assert rows[0]["title"] == "UniICL"
    assert rows[0]["authors"] == ["A", "B"]
