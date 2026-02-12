from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from paperbot.domain.identity import PaperIdentity
from paperbot.infrastructure.stores.models import PaperJudgeScoreModel
from paperbot.infrastructure.stores.paper_store import SqlAlchemyPaperStore
from paperbot.infrastructure.stores.research_store import SqlAlchemyResearchStore
from paperbot.infrastructure.stores.identity_store import IdentityStore


def _judged_report():
    return {
        "title": "Daily",
        "date": "2026-02-10",
        "generated_at": "2026-02-10T00:00:00+00:00",
        "source": "papers.cool",
        "sources": ["papers_cool"],
        "queries": [
            {
                "raw_query": "ICL压缩",
                "normalized_query": "icl compression",
                "top_items": [
                    {
                        "title": "UniICL",
                        "url": "https://arxiv.org/abs/2501.12345",
                        "pdf_url": "https://arxiv.org/pdf/2501.12345.pdf",
                        "authors": ["A"],
                        "snippet": "compress context",
                        "judge": {
                            "overall": 4.2,
                            "recommendation": "must_read",
                            "one_line_summary": "good",
                            "judge_model": "fake",
                            "judge_cost_tier": 1,
                            "relevance": {"score": 5},
                            "novelty": {"score": 4},
                            "rigor": {"score": 4},
                            "impact": {"score": 4},
                            "clarity": {"score": 4},
                        },
                    }
                ],
            }
        ],
        "global_top": [],
    }


def test_upsert_judge_scores_from_report_is_idempotent(tmp_path: Path):
    db_path = tmp_path / "judge-registry.db"
    store = SqlAlchemyPaperStore(db_url=f"sqlite:///{db_path}")

    report = _judged_report()
    first = store.upsert_judge_scores_from_report(report)
    second = store.upsert_judge_scores_from_report(report)

    assert first == {"total": 1, "created": 1, "updated": 0}
    assert second == {"total": 1, "created": 0, "updated": 1}

    with store._provider.session() as session:
        rows = session.execute(select(PaperJudgeScoreModel)).scalars().all()
        assert len(rows) == 1
        assert rows[0].query == "icl compression"
        assert float(rows[0].overall) == 4.2


def test_feedback_links_to_paper_registry_row(tmp_path: Path):
    db_path = tmp_path / "feedback-link.db"
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

    track = research_store.create_track(user_id="default", name="t1", activate=True)
    feedback = research_store.add_paper_feedback(
        user_id="default",
        track_id=int(track["id"]),
        paper_id="https://arxiv.org/abs/2501.12345",
        action="save",
        metadata={"url": "https://arxiv.org/abs/2501.12345", "title": "UniICL"},
    )

    assert feedback is not None
    assert feedback["paper_ref_id"] == int(paper["id"])


def test_saved_list_and_detail_from_research_store(tmp_path: Path):
    db_path = tmp_path / "saved-detail.db"
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

    track = research_store.create_track(user_id="u1", name="track-u1", activate=True)
    feedback = research_store.add_paper_feedback(
        user_id="u1",
        track_id=int(track["id"]),
        paper_id=str(paper["id"]),
        action="save",
        metadata={"title": "UniICL"},
    )
    assert feedback and feedback["paper_ref_id"] == int(paper["id"])

    status = research_store.set_paper_reading_status(
        user_id="u1",
        paper_id=str(paper["id"]),
        status="read",
        mark_saved=True,
    )
    assert status is not None
    assert status["status"] == "read"

    saved = research_store.list_saved_papers(user_id="u1", limit=10)
    assert len(saved) == 1
    assert saved[0]["paper"]["title"] == "UniICL"

    detail = research_store.get_paper_detail(user_id="u1", paper_id=str(paper["id"]))
    assert detail is not None
    assert detail["paper"]["title"] == "UniICL"
    assert detail["reading_status"]["status"] == "read"


def test_feedback_resolves_via_identity_store_mapping(tmp_path: Path):
    db_path = tmp_path / "identity-feedback.db"
    db_url = f"sqlite:///{db_path}"

    paper_store = SqlAlchemyPaperStore(db_url=db_url)
    research_store = SqlAlchemyResearchStore(db_url=db_url)
    identity_store = IdentityStore(db_url=db_url)

    paper = paper_store.upsert_paper(
        paper={
            "title": "CrossSource Paper",
            "url": "https://example.com/p/abc",
            "pdf_url": "https://example.com/p/abc.pdf",
        }
    )

    identity_store.upsert_identity(
        paper_id=int(paper["id"]),
        identity=PaperIdentity(source="papers_cool", external_id="pc:abc123"),
    )

    track = research_store.create_track(user_id="u2", name="track-u2", activate=True)
    feedback = research_store.add_paper_feedback(
        user_id="u2",
        track_id=int(track["id"]),
        paper_id="pc:abc123",
        action="save",
        metadata={},
    )

    assert feedback is not None
    assert feedback["paper_ref_id"] == int(paper["id"])
