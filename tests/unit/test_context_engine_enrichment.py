from __future__ import annotations

from paperbot.context_engine.engine import ContextEngine


class _FakePaperStore:
    def __init__(self):
        self.calls = []

    def get_latest_judge_scores(self, paper_ids):
        self.calls.append(list(paper_ids))
        return {
            1: {
                "overall": 4.6,
                "recommendation": "must_read",
                "one_line_summary": "Strong relevance",
                "judge_model": "judge-x",
                "scored_at": "2026-02-12T00:00:00+00:00",
            }
        }


def test_attach_latest_judge_only_for_numeric_ids():
    store = _FakePaperStore()
    engine = ContextEngine(
        research_store=object(),
        memory_store=object(),
        paper_store=store,
        track_router=object(),
    )
    papers = [
        {"paper_id": "1", "title": "A"},
        {"paper_id": "not-numeric", "title": "B"},
        {"paper_id": "", "title": "C"},
    ]

    engine._attach_latest_judge(papers)

    assert store.calls == [[1]]
    assert papers[0]["latest_judge"]["overall"] == 4.6
    assert "latest_judge" not in papers[1]
    assert "latest_judge" not in papers[2]


def test_attach_feedback_flags_marks_saved_and_liked():
    papers = [
        {"paper_id": "11", "title": "Saved only"},
        {"paper_id": "22", "title": "Saved + liked"},
        {"paper_id": "33", "title": "None"},
    ]

    ContextEngine._attach_feedback_flags(
        papers,
        saved_ids={"11", "22"},
        liked_ids={"22"},
    )

    assert papers[0].get("is_saved") is True
    assert papers[0].get("is_liked") is None
    assert papers[1].get("is_saved") is True
    assert papers[1].get("is_liked") is True
    assert papers[2].get("is_saved") is None
    assert papers[2].get("is_liked") is None
