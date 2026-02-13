"""merge structured_card and anchor_author branches

Revision ID: 4c71b28a2f67
Revises: 0016_structured_card, 0018_user_anchor_actions
Create Date: 2026-02-13 10:26:02.630387

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa



revision = '4c71b28a2f67'
down_revision = ('0016_structured_card', '0018_user_anchor_actions')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass


