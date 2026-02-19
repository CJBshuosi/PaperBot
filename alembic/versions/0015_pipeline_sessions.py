"""add pipeline session checkpoints table

Revision ID: 0015_pipeline_sessions
Revises: 0014_llm_usage
Create Date: 2026-02-12 22:10:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op


revision = "0015_pipeline_sessions"
down_revision = "0014_llm_usage"
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
    if _has_table("pipeline_sessions"):
        return

    op.create_table(
        "pipeline_sessions",
        sa.Column("session_id", sa.String(length=64), primary_key=True),
        sa.Column("workflow", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column("checkpoint", sa.String(length=64), nullable=False, server_default="init"),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("state_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    if not _has_index("pipeline_sessions", "ix_pipeline_sessions_workflow"):
        op.create_index("ix_pipeline_sessions_workflow", "pipeline_sessions", ["workflow"])
    if not _has_index("pipeline_sessions", "ix_pipeline_sessions_status"):
        op.create_index("ix_pipeline_sessions_status", "pipeline_sessions", ["status"])
    if not _has_index("pipeline_sessions", "ix_pipeline_sessions_checkpoint"):
        op.create_index("ix_pipeline_sessions_checkpoint", "pipeline_sessions", ["checkpoint"])
    if not _has_index("pipeline_sessions", "ix_pipeline_sessions_created_at"):
        op.create_index("ix_pipeline_sessions_created_at", "pipeline_sessions", ["created_at"])
    if not _has_index("pipeline_sessions", "ix_pipeline_sessions_updated_at"):
        op.create_index("ix_pipeline_sessions_updated_at", "pipeline_sessions", ["updated_at"])


def downgrade() -> None:
    if not _has_table("pipeline_sessions"):
        return

    for idx in [
        "ix_pipeline_sessions_updated_at",
        "ix_pipeline_sessions_created_at",
        "ix_pipeline_sessions_checkpoint",
        "ix_pipeline_sessions_status",
        "ix_pipeline_sessions_workflow",
    ]:
        if _has_index("pipeline_sessions", idx):
            op.drop_index(idx, table_name="pipeline_sessions")

    op.drop_table("pipeline_sessions")
