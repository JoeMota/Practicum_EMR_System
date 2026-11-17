"""Add medication verification / release orders."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "sprint7_04_medication_orders"
down_revision: Union[str, Sequence[str], None] = "sprint7_03_compound_meds"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "medication_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("medication_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("dose", sa.String(length=60), nullable=False),
        sa.Column("route", sa.String(length=40), nullable=False),
        sa.Column("frequency", sa.String(length=80), nullable=False),
        sa.Column("quantity", sa.String(length=60), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending_verify", nullable=False),
        sa.Column("submitted_by_id", sa.Uuid(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_by_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["medication_id"], ["medications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_medication_orders_patient_id", "medication_orders", ["patient_id"])
    op.create_index("ix_medication_orders_medication_id", "medication_orders", ["medication_id"])


def downgrade() -> None:
    op.drop_index("ix_medication_orders_medication_id", table_name="medication_orders")
    op.drop_index("ix_medication_orders_patient_id", table_name="medication_orders")
    op.drop_table("medication_orders")
