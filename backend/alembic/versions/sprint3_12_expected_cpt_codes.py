"""Add expected CPT codes to shared case answer keys.

Revision ID: sprint3_12_expected_cpt_codes
Revises: sprint3_11_activity_phase4
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "sprint3_12_expected_cpt_codes"
down_revision: Union[str, Sequence[str], None] = "sprint3_11_activity_phase4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "case_answer_keys",
        sa.Column(
            "expected_cpt_codes",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("case_answer_keys", "expected_cpt_codes")
