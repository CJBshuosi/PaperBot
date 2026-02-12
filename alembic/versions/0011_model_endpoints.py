"""add model endpoint gateway table

Revision ID: 0011_model_endpoints
Revises: 0010_contract_feedback_fk
Create Date: 2026-02-12 11:10:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op


revision = "0011_model_endpoints"
down_revision = "0010_contract_feedback_fk"
branch_labels = None
depends_on = None


def _is_offline() -> bool:
    try:
        return bool(context.is_offline_mode())
    except Exception:
        return False


def _inspector():
    bind = op.get_bind()
    return sa.inspect(bind)


def _has_table(name: str) -> bool:
    if _is_offline():
        return False
    return bool(_inspector().has_table(name))


def upgrade() -> None:
    if _has_table("model_endpoints"):
        return

    op.create_table(
        "model_endpoints",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column(
            "vendor", sa.String(length=32), nullable=False, server_default="openai_compatible"
        ),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column(
            "api_key_env", sa.String(length=64), nullable=False, server_default="OPENAI_API_KEY"
        ),
        sa.Column("models_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("task_types_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_model_endpoints_name"),
    )
    op.create_index("ix_model_endpoints_name", "model_endpoints", ["name"])
    op.create_index("ix_model_endpoints_enabled", "model_endpoints", ["enabled"])
    op.create_index("ix_model_endpoints_is_default", "model_endpoints", ["is_default"])


def downgrade() -> None:
    if not _has_table("model_endpoints"):
        return
    op.drop_index("ix_model_endpoints_is_default", table_name="model_endpoints")
    op.drop_index("ix_model_endpoints_enabled", table_name="model_endpoints")
    op.drop_index("ix_model_endpoints_name", table_name="model_endpoints")
    op.drop_table("model_endpoints")
