"""Session activity and acting role for idle logout and ADM-05."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "sprint9_01_session_activity"
down_revision: Union[str, Sequence[str], None] = "sprint8_01_sim_lab_checkin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("acting_role", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "acting_role")
    op.drop_column("users", "last_activity_at")
