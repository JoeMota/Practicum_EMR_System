"""Chart phase 1: medication access or cost, and vital attribution.

Revision ID: sprint3_09_chart_phase1
Revises: sprint3_08_client_answers
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "sprint3_09_chart_phase1"
down_revision: Union[str, Sequence[str], None] = "sprint3_08_client_answers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("medications", sa.Column("access_cost", sa.String(length=120), nullable=True))
    op.add_column(
        "vitals",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="recorded"),
    )
    op.add_column("vitals", sa.Column("recorded_by_name", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("vitals", "recorded_by_name")
    op.drop_column("vitals", "status")
    op.drop_column("medications", "access_cost")
