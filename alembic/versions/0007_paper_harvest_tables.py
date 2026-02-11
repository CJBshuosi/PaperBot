"""paper harvest tables

Revision ID: 0007_paper_harvest_tables
Revises: 0006_newsletter_subscribers
Create Date: 2026-02-06

Adds:
- papers: harvested paper metadata with multi-source deduplication
- harvest_runs: harvest execution tracking and audit
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "0007_paper_harvest_tables"
down_revision = "0006_newsletter_subscribers"
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
    _upgrade_create_tables()
    _upgrade_create_indexes()


def _upgrade_create_tables() -> None:
    # Papers table - harvested paper metadata
    if _is_offline() or not _has_table("papers"):
        op.create_table(
            "papers",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            # Canonical identifiers (for deduplication)
            sa.Column("doi", sa.String(length=256), nullable=True),
            sa.Column("arxiv_id", sa.String(length=64), nullable=True),
            sa.Column("semantic_scholar_id", sa.String(length=64), nullable=True),
            sa.Column("openalex_id", sa.String(length=64), nullable=True),
            sa.Column("title_hash", sa.String(length=64), nullable=False),
            # Core metadata
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("abstract", sa.Text(), server_default="", nullable=False),
            sa.Column("authors_json", sa.Text(), server_default="[]", nullable=False),
            sa.Column("year", sa.Integer(), nullable=True),
            sa.Column("venue", sa.String(length=256), nullable=True),
            sa.Column("publication_date", sa.String(length=32), nullable=True),
            sa.Column("citation_count", sa.Integer(), server_default="0", nullable=False),
            # URLs
            sa.Column("url", sa.String(length=1024), nullable=True),
            sa.Column("pdf_url", sa.String(length=1024), nullable=True),
            # Classification
            sa.Column("keywords_json", sa.Text(), server_default="[]", nullable=False),
            sa.Column("fields_of_study_json", sa.Text(), server_default="[]", nullable=False),
            # Source tracking
            sa.Column("primary_source", sa.String(length=32), nullable=False),
            sa.Column("sources_json", sa.Text(), server_default="[]", nullable=False),
            # Timestamps
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )

    # Harvest runs table - execution tracking
    if _is_offline() or not _has_table("harvest_runs"):
        op.create_table(
            "harvest_runs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.String(length=64), unique=True, nullable=False),
            # Input parameters
            sa.Column("keywords_json", sa.Text(), server_default="[]", nullable=False),
            sa.Column("venues_json", sa.Text(), server_default="[]", nullable=False),
            sa.Column("sources_json", sa.Text(), server_default="[]", nullable=False),
            sa.Column("max_results_per_source", sa.Integer(), server_default="100", nullable=False),
            # Results
            sa.Column("status", sa.String(length=32), server_default="running", nullable=False),
            sa.Column("papers_found", sa.Integer(), server_default="0", nullable=False),
            sa.Column("papers_new", sa.Integer(), server_default="0", nullable=False),
            sa.Column("papers_deduplicated", sa.Integer(), server_default="0", nullable=False),
            sa.Column("error_json", sa.Text(), server_default="{}", nullable=False),
            # Timestamps
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        )


def _upgrade_create_indexes() -> None:
    # Papers indexes
    _create_index("ix_papers_doi", "papers", ["doi"])
    _create_index("ix_papers_arxiv_id", "papers", ["arxiv_id"])
    _create_index("ix_papers_semantic_scholar_id", "papers", ["semantic_scholar_id"])
    _create_index("ix_papers_openalex_id", "papers", ["openalex_id"])
    _create_index("ix_papers_title_hash", "papers", ["title_hash"])
    _create_index("ix_papers_year", "papers", ["year"])
    _create_index("ix_papers_venue", "papers", ["venue"])
    _create_index("ix_papers_citation_count", "papers", ["citation_count"])
    _create_index("ix_papers_primary_source", "papers", ["primary_source"])
    _create_index("ix_papers_created_at", "papers", ["created_at"])

    # Harvest runs indexes
    _create_index("ix_harvest_runs_run_id", "harvest_runs", ["run_id"])
    _create_index("ix_harvest_runs_status", "harvest_runs", ["status"])
    _create_index("ix_harvest_runs_started_at", "harvest_runs", ["started_at"])


def downgrade() -> None:
    op.drop_table("harvest_runs")
    op.drop_table("papers")
