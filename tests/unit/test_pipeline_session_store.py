from __future__ import annotations

from pathlib import Path

from paperbot.infrastructure.stores.pipeline_session_store import PipelineSessionStore


def test_pipeline_session_store_resume_and_result(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / pipeline-session.db}"
    store = PipelineSessionStore(db_url=db_url)

    started = store.start_session(
        workflow="paperscool_daily",
        payload={"q": ["icl"]},
        session_id="sess-1",
        resume=False,
    )
    assert started["session_id"] == "sess-1"
    assert started["status"] == "running"

    cp = store.save_checkpoint(
        session_id="sess-1",
        checkpoint="report_built",
        state={"report": {"title": "Daily"}},
    )
    assert cp is not None
    assert cp["checkpoint"] == "report_built"

    done = store.save_result(
        session_id="sess-1",
        status="completed",
        result={"report": {"title": "Daily"}, "markdown": "# test"},
    )
    assert done is not None
    assert done["status"] == "completed"

    resumed = store.start_session(
        workflow="paperscool_daily",
        payload={"q": ["icl"]},
        session_id="sess-1",
        resume=True,
    )
    assert resumed["status"] == "completed"
    assert resumed["result"]["markdown"] == "# test"
