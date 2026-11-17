"""Course activity window for at-risk flags.

Revision ID: sprint3_11_activity_phase4
Revises: sprint3_10_case_phase2
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "sprint3_11_activity_phase4"
down_revision: Union[str, Sequence[str], None] = "sprint3_10_case_phase2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "courses",
        sa.Column("inactivity_days", sa.Integer(), server_default="7", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("courses", "inactivity_days")
