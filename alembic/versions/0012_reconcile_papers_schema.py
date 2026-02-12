"""reconcile papers schema with current ORM

Revision ID: 0012_reconcile_papers_schema
Revises: 0011_model_endpoints
Create Date: 2026-02-12 12:20:00

Adds missing columns/indexes on legacy `papers` table created before 0007.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op


revision = "0012_reconcile_papers_schema"
down_revision = "0011_model_endpoints"
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


def _has_index(table: str, index_name: str) -> bool:
    if _is_offline() or not _has_table(table):
        return False
    names = {str(i.get("name") or "") for i in _inspector().get_indexes(table)}
    return index_name in names


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if _is_offline() or column.name in _columns(table):
        return
    op.add_column(table, column)


def _create_index_if_possible(name: str, table: str, cols: list[str]) -> None:
    if _is_offline() or _has_index(table, name):
        return
    if not set(cols).issubset(_columns(table)):
        return
    op.create_index(name, table, cols)


def upgrade() -> None:
    if not _has_table("papers"):
        return

    _add_column_if_missing(
        "papers", sa.Column("semantic_scholar_id", sa.String(length=64), nullable=True)
    )
    _add_column_if_missing("papers", sa.Column("openalex_id", sa.String(length=64), nullable=True))
    _add_column_if_missing(
        "papers",
        sa.Column("title_hash", sa.String(length=64), nullable=False, server_default=""),
    )
    _add_column_if_missing("papers", sa.Column("year", sa.Integer(), nullable=True))
    _add_column_if_missing(
        "papers", sa.Column("publication_date", sa.String(length=32), nullable=True)
    )
    _add_column_if_missing(
        "papers", sa.Column("citation_count", sa.Integer(), nullable=False, server_default="0")
    )
    _add_column_if_missing(
        "papers",
        sa.Column("fields_of_study_json", sa.Text(), nullable=False, server_default="[]"),
    )
    _add_column_if_missing(
        "papers",
        sa.Column("primary_source", sa.String(length=32), nullable=False, server_default=""),
    )
    _add_column_if_missing(
        "papers",
        sa.Column("sources_json", sa.Text(), nullable=False, server_default="[]"),
    )
    _add_column_if_missing(
        "papers", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
    )

    # Fill empty title_hash so ORM non-null assumptions hold.
    if "title_hash" in _columns("papers"):
        op.execute(
            sa.text(
                """
                UPDATE papers
                SET title_hash = lower(hex(randomblob(16)))
                WHERE title_hash IS NULL OR title_hash = ''
                """
            )
        )

    _create_index_if_possible("ix_papers_semantic_scholar_id", "papers", ["semantic_scholar_id"])
    _create_index_if_possible("ix_papers_openalex_id", "papers", ["openalex_id"])
    _create_index_if_possible("ix_papers_title_hash", "papers", ["title_hash"])
    _create_index_if_possible("ix_papers_year", "papers", ["year"])
    _create_index_if_possible("ix_papers_venue", "papers", ["venue"])
    _create_index_if_possible("ix_papers_citation_count", "papers", ["citation_count"])
    _create_index_if_possible("ix_papers_primary_source", "papers", ["primary_source"])


def downgrade() -> None:
    # Keep columns for backward compatibility; only drop indexes created here.
    for idx in [
        "ix_papers_semantic_scholar_id",
        "ix_papers_openalex_id",
        "ix_papers_title_hash",
        "ix_papers_year",
        "ix_papers_venue",
        "ix_papers_citation_count",
        "ix_papers_primary_source",
    ]:
        if _has_index("papers", idx):
            op.drop_index(idx, table_name="papers")
