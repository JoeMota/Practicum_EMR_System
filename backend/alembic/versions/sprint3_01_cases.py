"""Case masters: past medical history and authorship.

Revision ID: sprint3_01_cases
Revises: c41d8a7e5b20
Create Date: 2026-10-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "sprint3_01_cases"
down_revision: Union[str, Sequence[str], None] = "c41d8a7e5b20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column("past_medical_history", sa.Text(), server_default="", nullable=False),
    )
    op.add_column("patients", sa.Column("created_by_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_patients_created_by_id_users"),
        "patients",
        "users",
        ["created_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_patients_created_by_id_users"), "patients", type_="foreignkey")
    op.drop_column("patients", "created_by_id")
    op.drop_column("patients", "past_medical_history")
