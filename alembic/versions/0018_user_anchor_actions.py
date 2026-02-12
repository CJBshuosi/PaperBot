"""add user_anchor_actions table

Revision ID: 0018_user_anchor_actions
Revises: 0017_user_anchor_scores
Create Date: 2026-02-13 00:25:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op


revision = "0018_user_anchor_actions"
down_revision = "0017_user_anchor_scores"
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


def _create_index(name: str, table: str, cols: list[str]) -> None:
    if _is_offline() or not _has_index(table, name):
        op.create_index(name, table, cols)


def upgrade() -> None:
    if not _has_table("user_anchor_actions"):
        op.create_table(
            "user_anchor_actions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column(
                "track_id", sa.Integer(), sa.ForeignKey("research_tracks.id"), nullable=False
            ),
            sa.Column(
                "author_id",
                sa.Integer(),
                sa.ForeignKey("authors.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("action", sa.String(length=16), nullable=False, server_default="follow"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "user_id",
                "track_id",
                "author_id",
                name="uq_user_anchor_actions_user_track_author",
            ),
        )

    _create_index("ix_user_anchor_actions_user_id", "user_anchor_actions", ["user_id"])
    _create_index("ix_user_anchor_actions_track_id", "user_anchor_actions", ["track_id"])
    _create_index("ix_user_anchor_actions_author_id", "user_anchor_actions", ["author_id"])
    _create_index("ix_user_anchor_actions_action", "user_anchor_actions", ["action"])
    _create_index("ix_user_anchor_actions_created_at", "user_anchor_actions", ["created_at"])
    _create_index("ix_user_anchor_actions_updated_at", "user_anchor_actions", ["updated_at"])


def downgrade() -> None:
    for idx in [
        "ix_user_anchor_actions_updated_at",
        "ix_user_anchor_actions_created_at",
        "ix_user_anchor_actions_action",
        "ix_user_anchor_actions_author_id",
        "ix_user_anchor_actions_track_id",
        "ix_user_anchor_actions_user_id",
    ]:
        if _has_index("user_anchor_actions", idx):
            op.drop_index(idx, table_name="user_anchor_actions")

    if _has_table("user_anchor_actions"):
        op.drop_table("user_anchor_actions")
