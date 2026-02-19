"""contract feedback fk read path

Revision ID: 0010_contract_feedback_fk
Revises: 0009_paper_identifiers
Create Date: 2026-02-12 08:05:00

Contract phase for canonical feedback join:
- Backfill canonical_paper_id from paper_ref_id when available.
- Add index optimized for library reads by canonical FK.
- Drop legacy paper_id index used by external-id joins.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op


revision = "0010_contract_feedback_fk"
down_revision = "0009_paper_identifiers"
branch_labels = None
depends_on = None


def _is_offline() -> bool:
    try:
        return bool(context.is_offline_mode())
    except Exception:
        return False


def _inspector():
    bind = op.get_bind()
    return sa.inspect(bind)


def _has_table(name: str) -> bool:
    if _is_offline():
        return False
    return bool(_inspector().has_table(name))


def _get_columns(table: str) -> set[str]:
    if _is_offline() or not _has_table(table):
        return set()
    return {c["name"] for c in _inspector().get_columns(table)}


def _has_index(table: str, index_name: str) -> bool:
    if _is_offline() or not _has_table(table):
        return False
    names = {idx.get("name") for idx in _inspector().get_indexes(table)}
    return index_name in names


def _create_index(name: str, table: str, cols: list[str]) -> None:
    if _is_offline() or _has_index(table, name):
        return
    op.create_index(name, table, cols)


def _drop_index(name: str, table: str) -> None:
    if _is_offline() or not _has_index(table, name):
        return
    op.drop_index(name, table_name=table)


def upgrade() -> None:
    if not _has_table("paper_feedback"):
        return

    cols = _get_columns("paper_feedback")
    if {"canonical_paper_id", "paper_ref_id"}.issubset(cols):
        op.execute(
            sa.text(
                """
                UPDATE paper_feedback
                SET canonical_paper_id = paper_ref_id
                WHERE canonical_paper_id IS NULL
                  AND paper_ref_id IS NOT NULL
                """
            )
        )

    _create_index(
        "ix_paper_feedback_user_action_canonical",
        "paper_feedback",
        ["user_id", "action", "canonical_paper_id"],
    )

    # Legacy external-id join path index.
    _drop_index("ix_paper_feedback_paper_id", "paper_feedback")


def downgrade() -> None:
    _create_index("ix_paper_feedback_paper_id", "paper_feedback", ["paper_id"])
    _drop_index("ix_paper_feedback_user_action_canonical", "paper_feedback")
