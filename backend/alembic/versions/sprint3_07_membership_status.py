"""Course membership can be deactivated without deleting the student.

Revision ID: sprint3_07_membership_status
Revises: sprint3_03_note_comments
Create Date: 2026-10-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "sprint3_07_membership_status"
down_revision: Union[str, Sequence[str], None] = "sprint3_03_note_comments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("course_memberships", sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("course_memberships", sa.Column("deactivated_by_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_course_memberships_deactivated_by_id_users"),
        "course_memberships",
        "users",
        ["deactivated_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_course_memberships_deactivated_by_id_users"), "course_memberships", type_="foreignkey")
    op.drop_column("course_memberships", "deactivated_by_id")
    op.drop_column("course_memberships", "deactivated_at")
