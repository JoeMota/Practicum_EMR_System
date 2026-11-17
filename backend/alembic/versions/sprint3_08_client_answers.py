"""Client-confirmed chart, grading, and account fields.

Revision ID: sprint3_08_client_answers
Revises: sprint3_07_membership_status
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "sprint3_08_client_answers"
down_revision: Union[str, Sequence[str], None] = "sprint3_07_membership_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LOCKS = (
    '{"medications": false, "allergies": false, "vitals": false, "labs": false, '
    '"diagnoses": true, "medical_history": true, "surgical_history": true, "chief_complaint": true}'
)


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column("section_locks", postgresql.JSONB(), nullable=False, server_default=sa.text(f"'{_LOCKS}'::jsonb")),
    )
    op.add_column(
        "patients",
        sa.Column("prefill_sections", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column("patients", sa.Column("unit", sa.String(length=80), nullable=True))
    op.add_column("patients", sa.Column("room", sa.String(length=40), nullable=True))
    op.add_column("patients", sa.Column("bed", sa.String(length=40), nullable=True))

    op.add_column(
        "allergies",
        sa.Column("category", sa.String(length=20), nullable=False, server_default="medication"),
    )
    op.add_column(
        "medications",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
    )
    op.add_column("medications", sa.Column("discontinued_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "medications",
        sa.Column("prescribed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("vitals", sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column(
        "clinical_notes",
        sa.Column("cpt_codes", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column("clinical_notes", sa.Column("rubric_scores", postgresql.JSONB(), nullable=True))
    op.add_column(
        "clinical_notes",
        sa.Column("body_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("courses", sa.Column("grading_guide", postgresql.JSONB(), nullable=True))

    op.add_column("users", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("portal_patient_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_users_portal_patient_id", "users", "patients", ["portal_patient_id"], ["id"])

    op.create_table(
        "chart_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chart_sessions_user_patient", "chart_sessions", ["user_id", "patient_id"])

    op.create_table(
        "medication_administrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("medication_id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("dose_given", sa.String(length=80), nullable=False),
        sa.Column("administered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default="pending_review"),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("reviewed_by_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["medication_id"], ["medications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_medication_administrations_patient", "medication_administrations", ["patient_id"])


def downgrade() -> None:
    op.drop_index("ix_medication_administrations_patient", table_name="medication_administrations")
    op.drop_table("medication_administrations")
    op.drop_index("ix_chart_sessions_user_patient", table_name="chart_sessions")
    op.drop_table("chart_sessions")
    op.drop_constraint("fk_users_portal_patient_id", "users", type_="foreignkey")
    op.drop_column("users", "portal_patient_id")
    op.drop_column("users", "purged_at")
    op.drop_column("users", "archived_at")
    op.drop_column("courses", "grading_guide")
    op.drop_column("clinical_notes", "body_locked")
    op.drop_column("clinical_notes", "rubric_scores")
    op.drop_column("clinical_notes", "cpt_codes")
    op.drop_column("vitals", "recorded_at")
    op.drop_column("medications", "prescribed")
    op.drop_column("medications", "discontinued_at")
    op.drop_column("medications", "status")
    op.drop_column("allergies", "category")
    op.drop_column("patients", "bed")
    op.drop_column("patients", "room")
    op.drop_column("patients", "unit")
    op.drop_column("patients", "prefill_sections")
    op.drop_column("patients", "section_locks")
