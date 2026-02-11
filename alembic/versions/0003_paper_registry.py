"""paper registry

Revision ID: 0003_paper_registry
Revises: 0002_research_eval_runs
Create Date: 2026-02-10

Adds canonical papers table for persistent DailyPaper ingestion.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op


revision = "0003_paper_registry"
down_revision = "0002_research_eval_runs"
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
    if _is_offline() or not _has_table("papers"):
        op.create_table(
            "papers",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("arxiv_id", sa.String(length=64), nullable=True),
            sa.Column("doi", sa.String(length=128), nullable=True),
            sa.Column("title", sa.Text(), server_default="", nullable=False),
            sa.Column("authors_json", sa.Text(), server_default="[]", nullable=False),
            sa.Column("abstract", sa.Text(), server_default="", nullable=False),
            sa.Column("url", sa.String(length=512), server_default="", nullable=False),
            sa.Column("external_url", sa.String(length=512), server_default="", nullable=False),
            sa.Column("pdf_url", sa.String(length=512), server_default="", nullable=False),
            sa.Column("source", sa.String(length=32), server_default="papers_cool", nullable=False),
            sa.Column("venue", sa.String(length=256), server_default="", nullable=False),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("keywords_json", sa.Text(), server_default="[]", nullable=False),
            sa.Column("metadata_json", sa.Text(), server_default="{}", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("arxiv_id", name="uq_papers_arxiv_id"),
            sa.UniqueConstraint("doi", name="uq_papers_doi"),
        )

    _create_index("ix_papers_arxiv_id", "papers", ["arxiv_id"])
    _create_index("ix_papers_doi", "papers", ["doi"])
    _create_index("ix_papers_title", "papers", ["title"])
    _create_index("ix_papers_source", "papers", ["source"])
    _create_index("ix_papers_published_at", "papers", ["published_at"])
    _create_index("ix_papers_first_seen_at", "papers", ["first_seen_at"])
    _create_index("ix_papers_created_at", "papers", ["created_at"])
    _create_index("ix_papers_updated_at", "papers", ["updated_at"])


def downgrade() -> None:
    op.drop_table("papers")
