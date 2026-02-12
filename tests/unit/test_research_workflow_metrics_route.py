from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from paperbot.api import main as api_main
from paperbot.api.routes import research as research_route
from paperbot.infrastructure.stores.workflow_metric_store import WorkflowMetricStore


def test_research_workflow_metrics_summary_route(tmp_path: Path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / workflow-route.db}"
    store = WorkflowMetricStore(db_url=db_url)
    store.record_metric(
        workflow="research_context",
        stage="auto",
        status="completed",
        track_id=3,
        claim_count=12,
        evidence_count=9,
        elapsed_ms=222,
    )

    monkeypatch.setattr(research_route, "_workflow_metric_store", store)

    with TestClient(api_main.app) as client:
        resp = client.get(
            "/api/research/metrics/workflows?days=7&workflow=research_context&track_id=3"
        )

    assert resp.status_code == 200
    summary = resp.json()["summary"]
    assert summary["totals"]["runs"] >= 1
    assert summary["totals"]["claim_count"] >= 12
    assert summary["totals"]["evidence_count"] >= 9
