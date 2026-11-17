"""Add lung sound exam findings for sim-lab documentation."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "sprint7_02_lung_sounds"
down_revision: Union[str, Sequence[str], None] = "sprint7_01_code_status_hipaa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lung_sounds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("location", sa.String(length=20), nullable=False),
        sa.Column("finding", sa.String(length=40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_by_name", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="recorded", nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lung_sounds_patient_id", "lung_sounds", ["patient_id"])


def downgrade() -> None:
    op.drop_index("ix_lung_sounds_patient_id", table_name="lung_sounds")
    op.drop_table("lung_sounds")
