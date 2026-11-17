"""Add simulated code status and HIPAA consent fields to patients."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "sprint7_01_code_status_hipaa"
down_revision: Union[str, Sequence[str], None] = "sprint6_02_merge_intake"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("code_status", sa.String(length=40), nullable=True))
    op.add_column("patients", sa.Column("advance_directive_notes", sa.Text(), nullable=True))
    op.add_column(
        "patients",
        sa.Column("hipaa_on_file", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("patients", sa.Column("hipaa_signed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("patients", sa.Column("hipaa_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("patients", "hipaa_note")
    op.drop_column("patients", "hipaa_signed_at")
    op.drop_column("patients", "hipaa_on_file")
    op.drop_column("patients", "advance_directive_notes")
    op.drop_column("patients", "code_status")
