"""Course switch for section assist."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "sprint5_01_assist"
down_revision: Union[str, Sequence[str], None] = "sprint4_03_guardrails"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("ai_assist", sa.Boolean(), server_default="false", nullable=False))


def downgrade() -> None:
    op.drop_column("courses", "ai_assist")
