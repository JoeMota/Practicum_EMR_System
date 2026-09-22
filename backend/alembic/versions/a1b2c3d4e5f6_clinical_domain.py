"""clinical domain: courses, patients, notes, scheduling + user profile fields

Revision ID: a1b2c3d4e5f6
Revises: 6b1ad8a5c6c1
Create Date: 2026-09-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "6b1ad8a5c6c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("university_id", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("phone_last4", sa.String(length=4), nullable=True))

    op.create_table(
        "courses",
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("term", sa.String(length=50), nullable=False),
        sa.Column("rubric_file_name", sa.String(length=255), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
    )
    op.create_index(op.f("ix_courses_code"), "courses", ["code"], unique=False)

    op.create_table(
        "enrollments",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("app_role", sa.String(length=30), nullable=False),
        sa.Column("discipline_code", sa.String(length=50), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name=op.f("fk_enrollments_course_id_courses"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_enrollments_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_enrollments")),
        sa.UniqueConstraint("user_id", "course_id", "app_role", "discipline_code", name="uq_enrollment_slot"),
    )
    op.create_index(op.f("ix_enrollments_course_id"), "enrollments", ["course_id"], unique=False)
    op.create_index(op.f("ix_enrollments_user_id"), "enrollments", ["user_id"], unique=False)

    op.create_table(
        "patients",
        sa.Column("mrn", sa.String(length=50), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("preferred_name", sa.String(length=100), nullable=True),
        sa.Column("dob", sa.String(length=20), nullable=False),
        sa.Column("age_years", sa.Integer(), nullable=False),
        sa.Column("sex_at_birth", sa.String(length=20), nullable=False),
        sa.Column("pronouns", sa.String(length=40), nullable=True),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("case_template_id", sa.String(length=80), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("is_training", sa.Boolean(), nullable=False),
        sa.Column("practice_label", sa.String(length=100), nullable=True),
        sa.Column("chief_complaint", sa.String(length=500), nullable=False),
        sa.Column("hpi", sa.String(length=4000), nullable=False),
        sa.Column("family_history", sa.String(length=2000), nullable=False),
        sa.Column("surgical_history", sa.String(length=2000), nullable=False),
        sa.Column("social_history", sa.String(length=2000), nullable=False),
        sa.Column("status", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("allergies", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("medications", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("problems", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("labs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("vitals", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("encounter", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("practice_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name=op.f("fk_patients_course_id_courses")),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name=op.f("fk_patients_owner_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patients")),
    )
    op.create_index(op.f("ix_patients_course_id"), "patients", ["course_id"], unique=False)
    op.create_index(op.f("ix_patients_mrn"), "patients", ["mrn"], unique=False)
    op.create_index(op.f("ix_patients_owner_id"), "patients", ["owner_id"], unique=False)

    op.create_table(
        "clinical_notes",
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.String(length=80), nullable=False),
        sa.Column("template_id", sa.String(length=50), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("author_name", sa.String(length=200), nullable=False),
        sa.Column("author_discipline", sa.String(length=50), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("diagnoses", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("feedback", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("addenda", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("routed_to_id", sa.Uuid(), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cosigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cosigned_by_name", sa.String(length=200), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], name=op.f("fk_clinical_notes_author_id_users")),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name=op.f("fk_clinical_notes_patient_id_patients")),
        sa.ForeignKeyConstraint(["routed_to_id"], ["users.id"], name=op.f("fk_clinical_notes_routed_to_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clinical_notes")),
    )
    op.create_index(op.f("ix_clinical_notes_author_id"), "clinical_notes", ["author_id"], unique=False)
    op.create_index(op.f("ix_clinical_notes_patient_id"), "clinical_notes", ["patient_id"], unique=False)
    op.create_index(op.f("ix_clinical_notes_routed_to_id"), "clinical_notes", ["routed_to_id"], unique=False)
    op.create_index(op.f("ix_clinical_notes_status"), "clinical_notes", ["status"], unique=False)

    op.create_table(
        "appointments",
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("when", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(length=200), nullable=False),
        sa.Column("with_whom", sa.String(length=200), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name=op.f("fk_appointments_patient_id_patients")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_appointments")),
    )
    op.create_index(op.f("ix_appointments_patient_id"), "appointments", ["patient_id"], unique=False)

    op.create_table(
        "referrals",
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("to_discipline", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("urgency", sa.String(length=20), nullable=False),
        sa.Column("created_by_name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name=op.f("fk_referrals_patient_id_patients")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_referrals")),
    )
    op.create_index(op.f("ix_referrals_patient_id"), "referrals", ["patient_id"], unique=False)


def downgrade() -> None:
    op.drop_table("referrals")
    op.drop_table("appointments")
    op.drop_table("clinical_notes")
    op.drop_table("patients")
    op.drop_table("enrollments")
    op.drop_table("courses")
    op.drop_column("users", "phone_last4")
    op.drop_column("users", "university_id")
