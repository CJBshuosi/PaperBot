from __future__ import annotations

from pathlib import Path

from paperbot.infrastructure.stores.model_endpoint_store import ModelEndpointStore


def test_activate_endpoint_switches_default(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / store-activate.db}"
    store = ModelEndpointStore(db_url=db_url)

    p1 = store.upsert_endpoint(
        payload={
            "name": "p1",
            "vendor": "openai_compatible",
            "api_key_env": "OPENAI_API_KEY",
            "models": ["gpt-4o-mini"],
            "enabled": True,
            "is_default": True,
        }
    )
    p2 = store.upsert_endpoint(
        payload={
            "name": "p2",
            "vendor": "openai_compatible",
            "api_key_env": "OPENAI_API_KEY",
            "models": ["gpt-4o"],
            "enabled": True,
            "is_default": False,
        }
    )

    activated = store.activate_endpoint(int(p2["id"]))
    assert activated is not None
    assert activated["id"] == int(p2["id"])
    assert activated["is_default"] is True

    rows = store.list_endpoints()
    row_by_name = {row["name"]: row for row in rows}
    assert row_by_name["p1"]["is_default"] is False
    assert row_by_name["p2"]["is_default"] is True


def test_delete_default_reassigns_new_default(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / store-delete.db}"
    store = ModelEndpointStore(db_url=db_url)

    p1 = store.upsert_endpoint(
        payload={
            "name": "p1",
            "vendor": "openai_compatible",
            "api_key_env": "OPENAI_API_KEY",
            "models": ["gpt-4o-mini"],
            "enabled": True,
            "is_default": True,
        }
    )
    p2 = store.upsert_endpoint(
        payload={
            "name": "p2",
            "vendor": "openai_compatible",
            "api_key_env": "OPENAI_API_KEY",
            "models": ["gpt-4o"],
            "enabled": True,
            "is_default": False,
        }
    )

    assert store.delete_endpoint(int(p1["id"])) is True

    rows = store.list_endpoints()
    assert len(rows) == 1
    assert rows[0]["id"] == int(p2["id"])
    assert rows[0]["is_default"] is True


def test_masked_api_key_write_back_keeps_existing_secret(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / store-mask.db}"
    store = ModelEndpointStore(db_url=db_url)

    created = store.upsert_endpoint(
        payload={
            "name": "masked-provider",
            "vendor": "openai_compatible",
            "api_key_env": "OPENAI_API_KEY",
            "api_key": "sk-live-1234567890",
            "models": ["gpt-4o-mini"],
            "enabled": True,
            "is_default": True,
        }
    )
    endpoint_id = int(created["id"])
    assert created["api_key"].startswith("***")

    updated = store.upsert_endpoint(
        payload={"api_key": created["api_key"]},
        endpoint_id=endpoint_id,
    )
    assert updated["api_key"] == created["api_key"]

    raw = store.get_endpoint(endpoint_id, include_secrets=True)
    assert raw is not None
    assert raw["api_key"] == "sk-live-1234567890"
