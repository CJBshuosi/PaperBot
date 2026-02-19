"""paper_identifiers table + paper_feedback.canonical_paper_id

Revision ID: 0009_paper_identifiers
Revises: 0008_paper_repos
Create Date: 2026-02-12

Expand phase: adds paper_identifiers mapping table and a nullable FK column
on paper_feedback for the dual-write migration.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "0009_paper_identifiers"
down_revision = "0008_paper_repos"
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


def _get_columns(table: str) -> set[str]:
    return {str(c["name"]) for c in _insp().get_columns(table)}


def _create_index(name: str, table: str, cols: list[str]) -> None:
    if _is_offline():
        op.create_index(name, table, cols)
        return
    if name in _get_indexes(table):
        return
    op.create_index(name, table, cols)


def upgrade() -> None:
    # --- paper_identifiers table ---
    if _is_offline() or not _has_table("paper_identifiers"):
        op.create_table(
            "paper_identifiers",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "paper_id",
                sa.Integer(),
                sa.ForeignKey("papers.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("source", sa.String(32), nullable=False),
            sa.Column("external_id", sa.String(256), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "source", "external_id", name="uq_paper_identifiers_source_eid"
            ),
        )

    _create_index("ix_paper_identifiers_paper_id", "paper_identifiers", ["paper_id"])
    _create_index(
        "ix_paper_identifiers_external_id", "paper_identifiers", ["external_id"]
    )

    # --- paper_feedback.canonical_paper_id (nullable FK for dual-write) ---
    if not _is_offline() and "canonical_paper_id" in _get_columns("paper_feedback"):
        pass  # column already exists
    else:
        op.add_column(
            "paper_feedback",
            sa.Column("canonical_paper_id", sa.Integer(), nullable=True),
        )
    _create_index(
        "ix_paper_feedback_canonical_paper_id",
        "paper_feedback",
        ["canonical_paper_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_paper_feedback_canonical_paper_id", table_name="paper_feedback")
    op.drop_column("paper_feedback", "canonical_paper_id")
    op.drop_table("paper_identifiers")
