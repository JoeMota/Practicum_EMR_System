"""Add course lifecycle status.

Revision ID: a9d81c3f2e71
Revises: 8d7590d48592
Create Date: 2026-10-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9d81c3f2e71"
down_revision: Union[str, Sequence[str], None] = "8d7590d48592"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "courses",
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("courses", "status")