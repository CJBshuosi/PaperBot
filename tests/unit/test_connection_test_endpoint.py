from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from paperbot.api import main as api_main
from paperbot.api.routes import model_endpoints as model_endpoints_route
from paperbot.infrastructure.stores.model_endpoint_store import ModelEndpointStore


def test_connection_test_returns_latency(tmp_path: Path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'conn-test.db'}"
    store = ModelEndpointStore(db_url=db_url)
    monkeypatch.setattr(model_endpoints_route, "_store", store)

    with TestClient(api_main.app) as client:
        created = client.post(
            "/api/model-endpoints",
            json={
                "name": "TestProvider",
                "vendor": "openai_compatible",
                "base_url": "https://test.example/v1",
                "api_key_env": "TEST_API_KEY",
                "api_key": "sk-test-key",
                "models": ["test/model"],
                "task_types": ["default"],
                "enabled": True,
            },
        )
        assert created.status_code == 200
        endpoint_id = created.json()["item"]["id"]

        resp = client.post(
            f"/api/model-endpoints/{endpoint_id}/test",
            json={"remote": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["success"] is True
        assert "latency_ms" in data
        assert isinstance(data["latency_ms"], int)
        assert data["latency_ms"] >= 0
        assert data["error"] is None
        assert data["endpoint_id"] == endpoint_id


def test_connection_test_not_found(tmp_path: Path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'conn-test-404.db'}"
    store = ModelEndpointStore(db_url=db_url)
    monkeypatch.setattr(model_endpoints_route, "_store", store)

    with TestClient(api_main.app) as client:
        resp = client.post("/api/model-endpoints/9999/test", json={"remote": False})
        assert resp.status_code == 404
