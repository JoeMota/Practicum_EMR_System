"""Simulation charts: phase, station assignments, and note kind."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "sprint6_01_simulation"
down_revision: Union[str, Sequence[str], None] = "sprint5_01_assist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("simulation_phase", sa.String(length=20), nullable=True))
    op.add_column(
        "clinical_notes",
        sa.Column("kind", sa.String(length=20), server_default="visit", nullable=False),
    )
    op.create_table(
        "simulation_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("station", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_id", "user_id", name="uq_simulation_patient_user"),
    )
    op.create_index("ix_simulation_assignments_patient_id", "simulation_assignments", ["patient_id"])
    op.create_index("ix_simulation_assignments_user_id", "simulation_assignments", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_simulation_assignments_user_id", table_name="simulation_assignments")
    op.drop_index("ix_simulation_assignments_patient_id", table_name="simulation_assignments")
    op.drop_table("simulation_assignments")
    op.drop_column("clinical_notes", "kind")
    op.drop_column("patients", "simulation_phase")
