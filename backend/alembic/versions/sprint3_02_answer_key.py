"""Answer keys live on the case master and stay off student charts.

Revision ID: sprint3_02_answer_key
Revises: sprint3_01_cases
Create Date: 2026-10-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "sprint3_02_answer_key"
down_revision: Union[str, Sequence[str], None] = "sprint3_01_cases"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("answer_key_released_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "case_answer_keys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("diagnoses", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("plan_points", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rationale", sa.Text(), server_default="", nullable=False),
        sa.Column("updated_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_id", name="uq_case_answer_keys_patient_id"),
    )


def downgrade() -> None:
    op.drop_table("case_answer_keys")
    op.drop_column("patients", "answer_key_released_at")
