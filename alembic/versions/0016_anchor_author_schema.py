"""add authors and paper_authors tables

Revision ID: 0016_anchor_author_schema
Revises: 0015_pipeline_sessions
Create Date: 2026-02-12 23:30:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op


revision = "0016_anchor_author_schema"
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


def _has_index(table: str, index_name: str) -> bool:
    if _is_offline() or not _has_table(table):
        return False
    names = {str(i.get("name") or "") for i in _inspector().get_indexes(table)}
    return index_name in names


def _create_index(name: str, table: str, cols: list[str]) -> None:
    if _is_offline() or not _has_index(table, name):
        op.create_index(name, table, cols)


def upgrade() -> None:
    if not _has_table("authors"):
        op.create_table(
            "authors",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("author_id", sa.String(length=128), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("slug", sa.String(length=256), nullable=False),
            sa.Column("h_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("citation_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("paper_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("anchor_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column(
                "anchor_level",
                sa.String(length=32),
                nullable=False,
                server_default="background",
            ),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("author_id", name="uq_authors_author_id"),
            sa.UniqueConstraint("slug", name="uq_authors_slug"),
        )

    _create_index("ix_authors_author_id", "authors", ["author_id"])
    _create_index("ix_authors_name", "authors", ["name"])
    _create_index("ix_authors_slug", "authors", ["slug"])
    _create_index("ix_authors_anchor_score", "authors", ["anchor_score"])
    _create_index("ix_authors_anchor_level", "authors", ["anchor_level"])
    _create_index("ix_authors_created_at", "authors", ["created_at"])
    _create_index("ix_authors_updated_at", "authors", ["updated_at"])

    if not _has_table("paper_authors"):
        op.create_table(
            "paper_authors",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "paper_id",
                sa.Integer(),
                sa.ForeignKey("papers.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "author_id",
                sa.Integer(),
                sa.ForeignKey("authors.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("author_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_corresponding", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("paper_id", "author_id", name="uq_paper_authors_paper_author"),
        )

    _create_index("ix_paper_authors_paper_id", "paper_authors", ["paper_id"])
    _create_index("ix_paper_authors_author_id", "paper_authors", ["author_id"])
    _create_index("ix_paper_authors_author_order", "paper_authors", ["author_order"])
    _create_index("ix_paper_authors_created_at", "paper_authors", ["created_at"])


def downgrade() -> None:
    for index in [
        "ix_paper_authors_created_at",
        "ix_paper_authors_author_order",
        "ix_paper_authors_author_id",
        "ix_paper_authors_paper_id",
    ]:
        if _has_index("paper_authors", index):
            op.drop_index(index, table_name="paper_authors")

    if _has_table("paper_authors"):
        op.drop_table("paper_authors")

    for index in [
        "ix_authors_updated_at",
        "ix_authors_created_at",
        "ix_authors_anchor_level",
        "ix_authors_anchor_score",
        "ix_authors_slug",
        "ix_authors_name",
        "ix_authors_author_id",
    ]:
        if _has_index("authors", index):
            op.drop_index(index, table_name="authors")

    if _has_table("authors"):
        op.drop_table("authors")
