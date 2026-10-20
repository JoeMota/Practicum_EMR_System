"""Allow the same course code in different terms."""
from typing import Sequence, Union

from alembic import op


revision: str = "c41d8a7e5b20"
down_revision: Union[str, Sequence[str], None] = "a9d81c3f2e71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_courses_code", "courses", type_="unique")
    op.create_unique_constraint("uq_courses_code_term", "courses", ["code", "term"])


def downgrade() -> None:
    # This downgrade fails if two terms already share a course code.
    op.drop_constraint("uq_courses_code_term", "courses", type_="unique")
    op.create_unique_constraint("uq_courses_code", "courses", ["code"])