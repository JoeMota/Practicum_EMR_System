"""Case phase 2: rubric and planted triggers live on the case master.

Revision ID: sprint3_10_case_phase2
Revises: sprint3_09_chart_phase1
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "sprint3_10_case_phase2"
down_revision: Union[str, Sequence[str], None] = "sprint3_09_chart_phase1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("grading_guide", postgresql.JSONB(), nullable=True))
    op.add_column(
        "patients",
        sa.Column("planted_triggers", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("patients", "planted_triggers")
    op.drop_column("patients", "grading_guide")
