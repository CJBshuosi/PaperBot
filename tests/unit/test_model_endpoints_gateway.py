from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from paperbot.api import main as api_main
from paperbot.api.routes import model_endpoints as model_endpoints_route
from paperbot.infrastructure.llm.router import ModelRouter
from paperbot.infrastructure.stores.model_endpoint_store import ModelEndpointStore


def test_model_endpoint_crud_routes(tmp_path: Path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / model-endpoints.db}"
    store = ModelEndpointStore(db_url=db_url)
    monkeypatch.setattr(model_endpoints_route, "_store", store)

    with TestClient(api_main.app) as client:
        created = client.post(
            "/api/model-endpoints",
            json={
                "name": "OpenRouter",
                "vendor": "openai_compatible",
                "base_url": "https://openrouter.ai/api/v1",
                "api_key_env": "OPENROUTER_API_KEY",
                "models": ["deepseek/deepseek-r1"],
                "task_types": ["reasoning", "summary"],
                "enabled": True,
                "is_default": True,
            },
        )
        assert created.status_code == 200
        endpoint_id = created.json()["item"]["id"]

        listed = client.get("/api/model-endpoints")
        assert listed.status_code == 200
        assert len(listed.json()["items"]) == 1

        updated = client.patch(
            f"/api/model-endpoints/{endpoint_id}",
            json={"models": ["deepseek/deepseek-r1", "openai/gpt-4o-mini"]},
        )
        assert updated.status_code == 200
        assert len(updated.json()["item"]["models"]) == 2

        tested = client.post(f"/api/model-endpoints/{endpoint_id}/test", json={"remote": False})
        assert tested.status_code == 200
        assert tested.json()["ok"] is True

        deleted = client.delete(f"/api/model-endpoints/{endpoint_id}")
        assert deleted.status_code == 200

        listed_again = client.get("/api/model-endpoints")
        assert listed_again.status_code == 200
        assert listed_again.json()["items"] == []


def test_model_router_reads_registry_before_env(tmp_path: Path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / router-registry.db}"
    store = ModelEndpointStore(db_url=db_url)
    store.upsert_endpoint(
        payload={
            "name": "GatewayDefault",
            "vendor": "openai_compatible",
            "base_url": "https://gateway.example/v1",
            "api_key_env": "GATEWAY_API_KEY",
            "models": ["gateway/model-a"],
            "task_types": ["default", "summary"],
            "enabled": True,
            "is_default": True,
        }
    )

    monkeypatch.setenv("PAPERBOT_DB_URL", db_url)
    router = ModelRouter.from_env()

    models = router.list_models()
    assert "GatewayDefault" in models
    assert models["GatewayDefault"] == "openai:gateway/model-a"
