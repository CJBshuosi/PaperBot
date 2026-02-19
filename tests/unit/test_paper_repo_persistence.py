from __future__ import annotations

from pathlib import Path

from paperbot.infrastructure.stores.paper_store import SqlAlchemyPaperStore
from paperbot.infrastructure.stores.research_store import SqlAlchemyResearchStore


def test_ingest_and_list_paper_repos(tmp_path: Path):
    db_path = tmp_path / "paper-repos.db"
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

    first = research_store.ingest_repo_enrichment_rows(
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
        ],
        source="test_repo_enrich",
    )

    assert first["total"] == 1
    assert first["created"] == 1
    assert first["updated"] == 0

    repos = research_store.list_paper_repos(paper_id=str(paper["id"]))
    assert repos is not None
    assert len(repos) == 1
    assert repos[0]["repo_url"] == "https://github.com/example/unicicl"
    assert repos[0]["stars"] == 321
    assert repos[0]["source"] == "test_repo_enrich"

    second = research_store.ingest_repo_enrichment_rows(
        rows=[
            {
                "title": "UniICL",
                "paper_url": "https://arxiv.org/abs/2501.12345",
                "repo_url": "https://github.com/example/unicicl",
                "github": {"full_name": "example/unicicl", "stars": 500},
            }
        ],
        source="test_repo_enrich",
    )

    assert second["total"] == 1
    assert second["created"] == 0
    assert second["updated"] == 1

    updated_repos = research_store.list_paper_repos(paper_id=str(paper["id"]))
    assert updated_repos is not None
    assert updated_repos[0]["stars"] == 500


def test_ingest_repo_rows_unresolved_paper(tmp_path: Path):
    db_path = tmp_path / "paper-repos-missing.db"
    db_url = f"sqlite:///{db_path}"
    _ = SqlAlchemyPaperStore(db_url=db_url)
    research_store = SqlAlchemyResearchStore(db_url=db_url)

    result = research_store.ingest_repo_enrichment_rows(
        rows=[
            {
                "title": "Unknown",
                "paper_url": "https://arxiv.org/abs/9999.99999",
                "repo_url": "https://github.com/example/unknown",
            }
        ]
    )

    assert result["total"] == 0
    assert result["unresolved_paper"] == 1
