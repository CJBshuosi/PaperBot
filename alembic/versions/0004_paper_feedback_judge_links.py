"""paper feedback/judge links

Revision ID: 0004_paper_feedback_judge_links
Revises: 0003_paper_registry
Create Date: 2026-02-10

Adds:
- paper_judge_scores table
- paper_feedback.paper_ref_id nullable FK-like reference column
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op


revision = "0004_paper_feedback_judge_links"
down_revision = "0003_paper_registry"
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


def _get_columns(table: str) -> set[str]:
    cols = set()
    for c in _insp().get_columns(table):
        cols.add(str(c.get("name") or ""))
    return cols


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
    if _is_offline() or not _has_table("paper_judge_scores"):
        op.create_table(
            "paper_judge_scores",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id"), nullable=False),
            sa.Column("query", sa.String(length=256), server_default="", nullable=False),
            sa.Column("overall", sa.Float(), server_default="0.0", nullable=False),
            sa.Column("relevance", sa.Float(), server_default="0.0", nullable=False),
            sa.Column("novelty", sa.Float(), server_default="0.0", nullable=False),
            sa.Column("rigor", sa.Float(), server_default="0.0", nullable=False),
            sa.Column("impact", sa.Float(), server_default="0.0", nullable=False),
            sa.Column("clarity", sa.Float(), server_default="0.0", nullable=False),
            sa.Column("recommendation", sa.String(length=32), server_default="", nullable=False),
            sa.Column("one_line_summary", sa.Text(), server_default="", nullable=False),
            sa.Column("judge_model", sa.String(length=128), server_default="", nullable=False),
            sa.Column("judge_cost_tier", sa.Integer(), nullable=True),
            sa.Column("scored_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("metadata_json", sa.Text(), server_default="{}", nullable=False),
            sa.UniqueConstraint("paper_id", "query", name="uq_paper_judge_scores_paper_query"),
        )

    _create_index("ix_paper_judge_scores_paper_id", "paper_judge_scores", ["paper_id"])
    _create_index("ix_paper_judge_scores_query", "paper_judge_scores", ["query"])
    _create_index("ix_paper_judge_scores_recommendation", "paper_judge_scores", ["recommendation"])
    _create_index("ix_paper_judge_scores_scored_at", "paper_judge_scores", ["scored_at"])

    if _is_offline():
        op.add_column("paper_feedback", sa.Column("paper_ref_id", sa.Integer(), nullable=True))
        op.create_index("ix_paper_feedback_paper_ref_id", "paper_feedback", ["paper_ref_id"])
        return

    if "paper_ref_id" not in _get_columns("paper_feedback"):
        with op.batch_alter_table("paper_feedback") as batch_op:
            batch_op.add_column(sa.Column("paper_ref_id", sa.Integer(), nullable=True))

    _create_index("ix_paper_feedback_paper_ref_id", "paper_feedback", ["paper_ref_id"])


def downgrade() -> None:
    with op.batch_alter_table("paper_feedback") as batch_op:
        try:
            batch_op.drop_index("ix_paper_feedback_paper_ref_id")
        except Exception:
            pass
        try:
            batch_op.drop_column("paper_ref_id")
        except Exception:
            pass

    op.drop_table("paper_judge_scores")
