"""Course guardrail profile and mode."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "sprint4_03_guardrails"
down_revision: Union[str, Sequence[str], None] = "sprint4_02_medication_reference"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "courses",
        sa.Column("guardrail_profile", sa.String(length=30), server_default="practicum", nullable=False),
    )
    op.add_column("courses", sa.Column("guardrail_mode", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("courses", "guardrail_mode")
    op.drop_column("courses", "guardrail_profile")
