"""add api key storage for model endpoints

Revision ID: 0013_model_endpoint_api_key
Revises: 0012_reconcile_papers_schema
Create Date: 2026-02-12 20:30:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op


revision = "0013_model_endpoint_api_key"
down_revision = "0012_reconcile_papers_schema"
branch_labels = None
depends_on = None


def _is_offline() -> bool:
    try:
        return bool(context.is_offline_mode())
    except Exception:
        return False


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    if _is_offline():
        return False
    return bool(_inspector().has_table(name))


def _columns(table: str) -> set[str]:
    if _is_offline() or not _has_table(table):
        return set()
    return {str(c.get("name") or "") for c in _inspector().get_columns(table)}


def upgrade() -> None:
    if not _has_table("model_endpoints"):
        return
    if "api_key_value" not in _columns("model_endpoints"):
        op.add_column(
            "model_endpoints", sa.Column("api_key_value", sa.String(length=512), nullable=True)
        )


def downgrade() -> None:
    if not _has_table("model_endpoints"):
        return
    if "api_key_value" in _columns("model_endpoints"):
        op.drop_column("model_endpoints", "api_key_value")
