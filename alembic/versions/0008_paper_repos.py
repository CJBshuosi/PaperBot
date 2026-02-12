"""paper repos enrichment table

Revision ID: 0008_paper_repos
Revises: 0007_paper_harvest_tables
Create Date: 2026-02-11

Adds paper_repos table to persist repository enrichment metadata linked to
canonical paper registry rows.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "0008_paper_repos"
down_revision = "0007_paper_harvest_tables"
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
    if _is_offline() or not _has_table("paper_repos"):
        op.create_table(
            "paper_repos",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id"), nullable=False),
            sa.Column("repo_url", sa.String(length=512), nullable=False, server_default=""),
            sa.Column("full_name", sa.String(length=256), nullable=False, server_default=""),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("stars", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("forks", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("open_issues", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("watchers", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("language", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("license", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("html_url", sa.String(length=512), nullable=False, server_default=""),
            sa.Column("topics_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("updated_at_remote", sa.DateTime(timezone=True), nullable=True),
            sa.Column("pushed_at_remote", sa.DateTime(timezone=True), nullable=True),
            sa.Column("query", sa.String(length=256), nullable=False, server_default=""),
            sa.Column(
                "source",
                sa.String(length=32),
                nullable=False,
                server_default="paperscool_repo_enrich",
            ),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("paper_id", "repo_url", name="uq_paper_repos_paper_repo"),
        )

    _create_index("ix_paper_repos_paper_id", "paper_repos", ["paper_id"])
    _create_index("ix_paper_repos_repo_url", "paper_repos", ["repo_url"])
    _create_index("ix_paper_repos_full_name", "paper_repos", ["full_name"])
    _create_index("ix_paper_repos_stars", "paper_repos", ["stars"])
    _create_index("ix_paper_repos_archived", "paper_repos", ["archived"])
    _create_index("ix_paper_repos_query", "paper_repos", ["query"])
    _create_index("ix_paper_repos_source", "paper_repos", ["source"])
    _create_index("ix_paper_repos_synced_at", "paper_repos", ["synced_at"])
    _create_index("ix_paper_repos_updated_at_remote", "paper_repos", ["updated_at_remote"])
    _create_index("ix_paper_repos_pushed_at_remote", "paper_repos", ["pushed_at_remote"])


def downgrade() -> None:
    op.drop_table("paper_repos")
