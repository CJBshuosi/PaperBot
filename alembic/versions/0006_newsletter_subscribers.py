"""newsletter subscribers

Revision ID: 0006_newsletter_subscribers
Revises: 0005_paper_reading_status
Create Date: 2026-02-11

Adds newsletter_subscribers table for email subscription management.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op


revision = "0006_newsletter_subscribers"
down_revision = "0005_paper_reading_status"
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
    if _is_offline() or not _has_table("newsletter_subscribers"):
        op.create_table(
            "newsletter_subscribers",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("email", sa.String(length=256), nullable=False, unique=True),
            sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
            sa.Column("unsub_token", sa.String(length=64), nullable=False, unique=True),
            sa.Column("subscribed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("unsub_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata_json", sa.Text(), server_default="{}", nullable=False),
        )

    _create_index("ix_newsletter_subscribers_email", "newsletter_subscribers", ["email"])
    _create_index("ix_newsletter_subscribers_status", "newsletter_subscribers", ["status"])
    _create_index("ix_newsletter_subscribers_subscribed_at", "newsletter_subscribers", ["subscribed_at"])


def downgrade() -> None:
    op.drop_table("newsletter_subscribers")
