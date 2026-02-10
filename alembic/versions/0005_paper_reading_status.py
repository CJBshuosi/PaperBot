"""paper reading status

Revision ID: 0005_paper_reading_status
Revises: 0004_paper_feedback_judge_links
Create Date: 2026-02-10

Adds paper_reading_status table for saved/reading/read lifecycle tracking.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op


revision = "0005_paper_reading_status"
down_revision = "0004_paper_feedback_judge_links"
branch_labels = None
depends_on = None


def _is_offline() -> bool:
    try:
        return bool(context.is_offline_mode())
    except Exception:
        return False


def _insp():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _insp().has_table(name)


def _get_indexes(table: str) -> set[str]:
    idx = set()
    for i in _insp().get_indexes(table):
        idx.add(str(i.get("name") or ""))
    return idx


def _create_index(name: str, table: str, cols: list[str]) -> None:
    if _is_offline():
        op.create_index(name, table, cols)
        return
    if name in _get_indexes(table):
        return
    op.create_index(name, table, cols)


def upgrade() -> None:
    if _is_offline() or not _has_table("paper_reading_status"):
        op.create_table(
            "paper_reading_status",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id"), nullable=False),
            sa.Column("status", sa.String(length=16), server_default="unread", nullable=False),
            sa.Column("saved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("metadata_json", sa.Text(), server_default="{}", nullable=False),
            sa.UniqueConstraint("user_id", "paper_id", name="uq_paper_reading_status_user_paper"),
        )

    _create_index("ix_paper_reading_status_user_id", "paper_reading_status", ["user_id"])
    _create_index("ix_paper_reading_status_paper_id", "paper_reading_status", ["paper_id"])
    _create_index("ix_paper_reading_status_status", "paper_reading_status", ["status"])
    _create_index("ix_paper_reading_status_saved_at", "paper_reading_status", ["saved_at"])
    _create_index("ix_paper_reading_status_read_at", "paper_reading_status", ["read_at"])
    _create_index("ix_paper_reading_status_created_at", "paper_reading_status", ["created_at"])
    _create_index("ix_paper_reading_status_updated_at", "paper_reading_status", ["updated_at"])


def downgrade() -> None:
    op.drop_table("paper_reading_status")
