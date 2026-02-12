from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, desc, select

from paperbot.infrastructure.stores.models import Base, ModelEndpointModel
from paperbot.infrastructure.stores.sqlalchemy_db import SessionProvider, get_db_url

_ALLOWED_VENDORS = {
    "openai",
    "openai_compatible",
    "anthropic",
    "ollama",
}

_ALLOWED_TASK_TYPES = {
    "default",
    "extraction",
    "summary",
    "analysis",
    "reasoning",
    "code",
    "review",
    "chat",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ModelEndpointStore:
    def __init__(self, db_url: Optional[str] = None, *, auto_create_schema: bool = True):
        self.db_url = db_url or get_db_url()
        self._provider = SessionProvider(self.db_url)
        if auto_create_schema:
            Base.metadata.create_all(self._provider.engine)

    def list_endpoints(self, *, enabled_only: bool = False) -> List[Dict[str, Any]]:
        with self._provider.session() as session:
            stmt = select(ModelEndpointModel)
            if enabled_only:
                stmt = stmt.where(ModelEndpointModel.enabled.is_(True))
            stmt = stmt.order_by(desc(ModelEndpointModel.is_default), ModelEndpointModel.name)
            rows = session.execute(stmt).scalars().all()
            return [self._to_dict(row) for row in rows]

    def get_endpoint(self, endpoint_id: int) -> Optional[Dict[str, Any]]:
        with self._provider.session() as session:
            row = session.execute(
                select(ModelEndpointModel).where(ModelEndpointModel.id == int(endpoint_id))
            ).scalar_one_or_none()
            return self._to_dict(row) if row else None

    def upsert_endpoint(
        self,
        *,
        payload: Dict[str, Any],
        endpoint_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        now = _utcnow()
        with self._provider.session() as session:
            row: Optional[ModelEndpointModel] = None
            if endpoint_id is not None:
                row = session.execute(
                    select(ModelEndpointModel).where(ModelEndpointModel.id == int(endpoint_id))
                ).scalar_one_or_none()

            creating = row is None
            if row is None:
                row = ModelEndpointModel(
                    name="",
                    vendor="openai_compatible",
                    api_key_env="OPENAI_API_KEY",
                    models_json="[]",
                    task_types_json="[]",
                    enabled=True,
                    is_default=False,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)

            name = str(payload.get("name") or row.name or "").strip()
            if not name:
                raise ValueError("name is required")
            vendor = str(payload.get("vendor") or row.vendor or "openai_compatible").strip().lower()
            if vendor not in _ALLOWED_VENDORS:
                raise ValueError(f"unsupported vendor: {vendor}")

            models = payload.get("models")
            if models is None:
                models = row.get_models()
            if not isinstance(models, list):
                models = [str(models)]
            normalized_models = [str(x).strip() for x in models if str(x).strip()]
            if not normalized_models:
                raise ValueError("at least one model is required")

            task_types = payload.get("task_types")
            if task_types is None:
                task_types = row.get_task_types()
            if not isinstance(task_types, list):
                task_types = [str(task_types)]
            normalized_tasks = sorted(
                {
                    str(x).strip().lower()
                    for x in task_types
                    if str(x).strip().lower() in _ALLOWED_TASK_TYPES
                }
            )

            row.name = name
            row.vendor = vendor
            row.base_url = str(payload.get("base_url") or row.base_url or "").strip() or None
            row.api_key_env = (
                str(payload.get("api_key_env") or row.api_key_env or "OPENAI_API_KEY").strip()
                or "OPENAI_API_KEY"
            )
            row.enabled = bool(payload.get("enabled", row.enabled))
            row.is_default = bool(payload.get("is_default", row.is_default))
            row.set_models(normalized_models)
            row.set_task_types(normalized_tasks)
            row.updated_at = now
            if creating:
                row.created_at = now

            session.flush()

            if row.is_default:
                session.execute(
                    ModelEndpointModel.__table__.update()
                    .where(ModelEndpointModel.id != row.id)
                    .values(is_default=False, updated_at=now)
                )
            elif not session.execute(
                select(ModelEndpointModel).where(ModelEndpointModel.is_default.is_(True)).limit(1)
            ).scalar_one_or_none():
                # Ensure there is always one default endpoint for fallback routing.
                row.is_default = True

            session.commit()
            session.refresh(row)
            return self._to_dict(row)

    def delete_endpoint(self, endpoint_id: int) -> bool:
        with self._provider.session() as session:
            row = session.execute(
                select(ModelEndpointModel).where(ModelEndpointModel.id == int(endpoint_id))
            ).scalar_one_or_none()
            if row is None:
                return False
            deleted_default = bool(row.is_default)
            session.execute(
                delete(ModelEndpointModel).where(ModelEndpointModel.id == int(endpoint_id))
            )
            session.flush()

            if deleted_default:
                replacement = session.execute(
                    select(ModelEndpointModel).order_by(ModelEndpointModel.id.asc()).limit(1)
                ).scalar_one_or_none()
                if replacement is not None:
                    replacement.is_default = True
                    replacement.updated_at = _utcnow()
                    session.add(replacement)

            session.commit()
            return True

    @staticmethod
    def _to_dict(row: ModelEndpointModel) -> Dict[str, Any]:
        models = row.get_models()
        task_types = row.get_task_types()
        key_present = bool(os.getenv(row.api_key_env or ""))
        return {
            "id": int(row.id),
            "name": row.name,
            "vendor": row.vendor,
            "base_url": row.base_url,
            "api_key_env": row.api_key_env,
            "models": models,
            "task_types": task_types,
            "enabled": bool(row.enabled),
            "is_default": bool(row.is_default),
            "api_key_present": key_present,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    def close(self) -> None:
        try:
            self._provider.engine.dispose()
        except Exception:
            pass
