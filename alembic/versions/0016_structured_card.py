"""add structured_card_json to papers

Revision ID: 0016_structured_card
Revises: 0015_pipeline_sessions
Create Date: 2026-02-12 23:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op


revision = "0016_structured_card"
down_revision = "0015_pipeline_sessions"
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


def _has_column(table: str, column: str) -> bool:
    if _is_offline() or not _has_table(table):
        return False
    cols = {str(c["name"]) for c in _inspector().get_columns(table)}
    return column in cols


def upgrade() -> None:
    if not _has_table("papers"):
        return
    if _has_column("papers", "structured_card_json"):
        return
    op.add_column("papers", sa.Column("structured_card_json", sa.Text(), nullable=True))


def downgrade() -> None:
    if not _has_table("papers"):
        return
    if not _has_column("papers", "structured_card_json"):
        return
    op.drop_column("papers", "structured_card_json")
