from __future__ import annotations

from pathlib import Path

from paperbot.infrastructure.stores.workflow_metric_store import WorkflowMetricStore


def test_workflow_metric_store_records_and_summarizes(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / workflow-metrics.db}"
    store = WorkflowMetricStore(db_url=db_url)

    store.record_metric(
        workflow="paperscool_daily",
        stage="result",
        status="completed",
        claim_count=10,
        evidence_count=8,
        elapsed_ms=1200,
        detail={"source": "test"},
    )
    store.record_metric(
        workflow="research_context",
        stage="auto",
        status="failed",
        claim_count=4,
        evidence_count=2,
        elapsed_ms=600,
        detail={"error": "boom"},
    )

    summary = store.summarize(days=7)

    assert summary["totals"]["runs"] == 2
    assert summary["totals"]["success_runs"] == 1
    assert summary["totals"]["failed_runs"] == 1
    assert summary["totals"]["claim_count"] == 14
    assert summary["totals"]["evidence_count"] == 10
    assert summary["totals"]["coverage_rate"] == round(10 / 14, 4)
    assert len(summary["by_workflow"]) == 2


def test_workflow_metric_store_filters_by_workflow_and_track(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / workflow-filter.db}"
    store = WorkflowMetricStore(db_url=db_url)

    store.record_metric(
        workflow="research_context",
        stage="auto",
        status="completed",
        track_id=1,
        claim_count=6,
        evidence_count=6,
    )
    store.record_metric(
        workflow="research_context",
        stage="auto",
        status="completed",
        track_id=2,
        claim_count=5,
        evidence_count=4,
    )

    scoped = store.summarize(days=7, workflow="research_context", track_id=1)
    assert scoped["totals"]["runs"] == 1
    assert scoped["totals"]["claim_count"] == 6
    assert scoped["totals"]["coverage_rate"] == 1.0
