"""Section comments on notes in review.

Revision ID: sprint3_03_note_comments
Revises: sprint3_02_answer_key
Create Date: 2026-10-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "sprint3_03_note_comments"
down_revision: Union[str, Sequence[str], None] = "sprint3_02_answer_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("note_comments", sa.Column("section_id", sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column("note_comments", "section_id")
