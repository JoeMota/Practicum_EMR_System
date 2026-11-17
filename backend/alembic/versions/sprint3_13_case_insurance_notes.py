"""Add insurance scenario notes to patient charts."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "sprint3_13_case_insurance_notes"
down_revision: Union[str, Sequence[str], None] = "sprint3_12_expected_cpt_codes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("insurance_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("patients", "insurance_notes")
