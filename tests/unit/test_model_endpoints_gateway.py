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

        created2 = client.post(
            "/api/model-endpoints",
            json={
                "name": "AltProvider",
                "vendor": "openai_compatible",
                "base_url": "https://alt.example/v1",
                "api_key_env": "ALT_API_KEY",
                "models": ["alt/model-x"],
                "task_types": ["default"],
                "enabled": True,
                "is_default": False,
            },
        )
        assert created2.status_code == 200
        endpoint2_id = created2.json()["item"]["id"]

        listed = client.get("/api/model-endpoints")
        assert listed.status_code == 200
        assert len(listed.json()["items"]) == 2

        updated = client.patch(
            f"/api/model-endpoints/{endpoint_id}",
            json={"models": ["deepseek/deepseek-r1", "openai/gpt-4o-mini"]},
        )
        assert updated.status_code == 200
        assert len(updated.json()["item"]["models"]) == 2

        tested = client.post(f"/api/model-endpoints/{endpoint_id}/test", json={"remote": False})
        assert tested.status_code == 200
        assert tested.json()["ok"] is True

        activated = client.post(f"/api/model-endpoints/{endpoint2_id}/activate")
        assert activated.status_code == 200
        assert activated.json()["item"]["id"] == endpoint2_id
        assert activated.json()["item"]["is_default"] is True

        listed_after_activate = client.get("/api/model-endpoints")
        assert listed_after_activate.status_code == 200
        items = listed_after_activate.json()["items"]
        defaults = [item for item in items if item["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["id"] == endpoint2_id

        deleted = client.delete(f"/api/model-endpoints/{endpoint_id}")
        assert deleted.status_code == 200

        deleted2 = client.delete(f"/api/model-endpoints/{endpoint2_id}")
        assert deleted2.status_code == 200

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


def test_model_router_applies_task_routes_from_registry(tmp_path: Path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / router-routing.db}"
    store = ModelEndpointStore(db_url=db_url)
    store.upsert_endpoint(
        payload={
            "name": "SummaryProvider",
            "vendor": "openai_compatible",
            "base_url": "https://summary.example/v1",
            "api_key_env": "SUMMARY_API_KEY",
            "models": ["summary/model"],
            "task_types": ["summary"],
            "enabled": True,
            "is_default": False,
        }
    )
    store.upsert_endpoint(
        payload={
            "name": "ReasoningProvider",
            "vendor": "openai_compatible",
            "base_url": "https://reasoning.example/v1",
            "api_key_env": "REASONING_API_KEY",
            "models": ["reasoning/model"],
            "task_types": ["reasoning", "review"],
            "enabled": True,
            "is_default": False,
        }
    )
    store.upsert_endpoint(
        payload={
            "name": "DefaultProvider",
            "vendor": "openai_compatible",
            "base_url": "https://default.example/v1",
            "api_key_env": "DEFAULT_API_KEY",
            "models": ["default/model"],
            "task_types": ["chat", "default"],
            "enabled": True,
            "is_default": True,
        }
    )

    monkeypatch.setenv("PAPERBOT_DB_URL", db_url)
    router = ModelRouter.from_env()

    assert router._task_routing["summary"] == "SummaryProvider"
    assert router._task_routing["reasoning"] == "ReasoningProvider"
    assert router._task_routing["review"] == "ReasoningProvider"
    assert router._task_routing["chat"] == "DefaultProvider"
    assert router._task_routing["default"] == "DefaultProvider"
