"""Saved note templates, sensitive notes, and patient photos."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "sprint3_14_templates_photo"
down_revision: Union[str, Sequence[str], None] = "sprint3_13_case_insurance_notes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("photo", sa.LargeBinary(), nullable=True))
    op.add_column("patients", sa.Column("photo_content_type", sa.String(length=40), nullable=True))
    op.add_column(
        "clinical_notes",
        sa.Column("sensitive", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_table(
        "note_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("discipline", sa.String(length=40), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=True),
        sa.Column("sensitive", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("sections", postgresql.JSONB(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_note_templates_course_id", "note_templates", ["course_id"])


def downgrade() -> None:
    op.drop_index("ix_note_templates_course_id", table_name="note_templates")
    op.drop_table("note_templates")
    op.drop_column("clinical_notes", "sensitive")
    op.drop_column("patients", "photo_content_type")
    op.drop_column("patients", "photo")
