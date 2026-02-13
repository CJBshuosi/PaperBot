from __future__ import annotations

from pathlib import Path

from paperbot.application.services.author_backfill_service import run_author_backfill
from paperbot.infrastructure.stores.author_store import AuthorStore
from paperbot.infrastructure.stores.paper_store import PaperStore


def test_run_author_backfill_is_idempotent(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / 'author-backfill.db'}"
    paper_store = PaperStore(db_url=db_url)

    paper = paper_store.upsert_paper(
        paper={
            "title": "Paper A",
            "paper_id": "2401.00001",
            "url": "https://arxiv.org/abs/2401.00001",
            "authors": [" Alice  Smith ", "Bob Lee", "alice smith", ""],
        },
        source_hint="arxiv",
    )
    paper_store.upsert_paper(
        paper={
            "title": "Paper B",
            "paper_id": "2401.00002",
            "url": "https://arxiv.org/abs/2401.00002",
            "authors": [],
        },
        source_hint="arxiv",
    )

    first_stats = run_author_backfill(db_url=db_url)
    assert first_stats["scanned_papers"] == 2
    assert first_stats["processed_papers"] == 1
    assert first_stats["skipped_no_authors"] == 1
    assert first_stats["new_authors"] == 2
    assert first_stats["new_relations"] == 2

    author_store = AuthorStore(db_url=db_url)
    linked = author_store.get_paper_authors(paper_id=int(paper["id"]))
    assert [row["name"] for row in linked] == ["Alice Smith", "Bob Lee"]

    second_stats = run_author_backfill(db_url=db_url)
    assert second_stats["processed_papers"] == 0
    assert second_stats["skipped_unchanged"] == 1
    assert second_stats["new_authors"] == 0
    assert second_stats["new_relations"] == 0
