"""add llm usage tracking table

Revision ID: 0014_llm_usage
Revises: 0013_model_endpoint_api_key
Create Date: 2026-02-12 21:25:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op


revision = "0014_llm_usage"
down_revision = "0013_model_endpoint_api_key"
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


def _has_index(table: str, index_name: str) -> bool:
    if _is_offline() or not _has_table(table):
        return False
    names = {str(i.get("name") or "") for i in _inspector().get_indexes(table)}
    return index_name in names


def upgrade() -> None:
    if _has_table("llm_usage"):
        return

    op.create_table(
        "llm_usage",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("task_type", sa.String(length=32), nullable=False, server_default="default"),
        sa.Column("provider_name", sa.String(length=64), nullable=False, server_default="unknown"),
        sa.Column("model_name", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
    )

    if not _has_index("llm_usage", "ix_llm_usage_ts"):
        op.create_index("ix_llm_usage_ts", "llm_usage", ["ts"])
    if not _has_index("llm_usage", "ix_llm_usage_task_type"):
        op.create_index("ix_llm_usage_task_type", "llm_usage", ["task_type"])
    if not _has_index("llm_usage", "ix_llm_usage_provider_name"):
        op.create_index("ix_llm_usage_provider_name", "llm_usage", ["provider_name"])
    if not _has_index("llm_usage", "ix_llm_usage_model_name"):
        op.create_index("ix_llm_usage_model_name", "llm_usage", ["model_name"])
    if not _has_index("llm_usage", "ix_llm_usage_total_tokens"):
        op.create_index("ix_llm_usage_total_tokens", "llm_usage", ["total_tokens"])


def downgrade() -> None:
    if not _has_table("llm_usage"):
        return
    for idx in [
        "ix_llm_usage_total_tokens",
        "ix_llm_usage_model_name",
        "ix_llm_usage_provider_name",
        "ix_llm_usage_task_type",
        "ix_llm_usage_ts",
    ]:
        if _has_index("llm_usage", idx):
            op.drop_index(idx, table_name="llm_usage")
    op.drop_table("llm_usage")
