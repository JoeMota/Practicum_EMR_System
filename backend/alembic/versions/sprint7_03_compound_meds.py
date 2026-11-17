"""Add compounded medication teaching fields."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "sprint7_03_compound_meds"
down_revision: Union[str, Sequence[str], None] = "sprint7_02_lung_sounds"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "medications",
        sa.Column("is_compound", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("medications", sa.Column("compound_ingredients", sa.Text(), nullable=True))
    op.add_column("medications", sa.Column("compound_vehicle", sa.String(length=120), nullable=True))
    op.add_column("medications", sa.Column("compound_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("medications", "compound_reason")
    op.drop_column("medications", "compound_vehicle")
    op.drop_column("medications", "compound_ingredients")
    op.drop_column("medications", "is_compound")
