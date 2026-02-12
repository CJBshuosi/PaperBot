from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from paperbot.api import main as api_main
from paperbot.api.routes import research as research_route
from paperbot.infrastructure.stores.workflow_metric_store import WorkflowMetricStore


def test_evidence_coverage_endpoint(tmp_path: Path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'coverage.db'}"
    store = WorkflowMetricStore(db_url=db_url)

    store.record_metric(
        workflow="research_context",
        stage="auto",
        status="completed",
        track_id=1,
        claim_count=20,
        evidence_count=15,
        elapsed_ms=100,
    )
    store.record_metric(
        workflow="research_context",
        stage="auto",
        status="completed",
        track_id=1,
        claim_count=10,
        evidence_count=8,
        elapsed_ms=80,
    )

    monkeypatch.setattr(research_route, "_workflow_metric_store", store)

    with TestClient(api_main.app) as client:
        resp = client.get("/api/research/metrics/evidence-coverage?days=7")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_claims"] == 30
    assert data["total_with_evidence"] == 23
    assert data["coverage_rate"] > 0
    assert isinstance(data["trend"], list)
    assert len(data["trend"]) >= 1
    assert "date" in data["trend"][0]
    assert "rate" in data["trend"][0]
