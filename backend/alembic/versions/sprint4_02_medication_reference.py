"""Medication identity and dose flags."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "sprint4_02_medication_reference"
down_revision: Union[str, Sequence[str], None] = "sprint4_01_access"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("medications", sa.Column("rxcui", sa.String(length=20), nullable=True))
    op.add_column("medications", sa.Column("generic_name", sa.String(length=120), nullable=True))
    op.add_column(
        "medications",
        sa.Column("brand_names", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
    )
    op.add_column(
        "medications",
        sa.Column("flags", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("medications", "flags")
    op.drop_column("medications", "brand_names")
    op.drop_column("medications", "generic_name")
    op.drop_column("medications", "rxcui")
