import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.user import User


class Course(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("code", "term", name="uq_courses_code_term"),)

    code: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(200))
    term: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    rubric_file_name: Mapped[str | None] = mapped_column(String(255))


class CourseMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "course_memberships"
    __table_args__ = (UniqueConstraint("user_id", "course_id", "role_id", name="uq_membership_user_course_role"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    discipline_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("disciplines.id"))

    user: Mapped[User] = relationship(back_populates="memberships")
    course: Mapped[Course] = relationship()
    role: Mapped["Role"] = relationship()
    discipline: Mapped["Discipline"] = relationship()


class Patient(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "patients"

    mrn: Mapped[str] = mapped_column(String(40), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    preferred_name: Mapped[str | None] = mapped_column(String(100))
    dob: Mapped[date] = mapped_column(Date)
    sex_at_birth: Mapped[str] = mapped_column(String(20))
    pronouns: Mapped[str | None] = mapped_column(String(40))
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"), index=True)
    mode: Mapped[str] = mapped_column(String(20))
    case_key: Mapped[str] = mapped_column(String(50))
    source_patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patients.id"))
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    practice_label: Mapped[str | None] = mapped_column(String(80))
    chief_complaint: Mapped[str] = mapped_column(Text)
    hpi: Mapped[str] = mapped_column(Text)
    lifecycle: Mapped[str] = mapped_column(String(40))
    encounter_status: Mapped[str] = mapped_column(String(40))
    care_setting: Mapped[str] = mapped_column(String(40))
    program: Mapped[str | None] = mapped_column(String(80))
    family_history: Mapped[str] = mapped_column(Text, default="")
    surgical_history: Mapped[str] = mapped_column(Text, default="")
    social_history: Mapped[str] = mapped_column(Text, default="")
    insurance_payer: Mapped[str | None] = mapped_column(String(120))
    insurance_member_id: Mapped[str | None] = mapped_column(String(60))
    insurance_group_number: Mapped[str | None] = mapped_column(String(60))
    emergency_contact_name: Mapped[str | None] = mapped_column(String(120))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(40))
    emergency_contact_relationship: Mapped[str | None] = mapped_column(String(60))
    is_training: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    owner: Mapped[User | None] = relationship(lazy="selectin")
    allergies: Mapped[list["Allergy"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    medications: Mapped[list["Medication"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    problems: Mapped[list["Problem"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    labs: Mapped[list["LabResult"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    vitals: Mapped[list["Vital"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    encounter: Mapped["Encounter | None"] = relationship(
        cascade="all, delete-orphan", lazy="selectin", uselist=False
    )


class Allergy(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "allergies"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    substance: Mapped[str] = mapped_column(String(120))
    reaction: Mapped[str | None] = mapped_column(String(120))
    severity: Mapped[str | None] = mapped_column(String(20))


class Medication(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "medications"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    dose: Mapped[str] = mapped_column(String(60))
    route: Mapped[str] = mapped_column(String(40))
    frequency: Mapped[str] = mapped_column(String(80))
    indication: Mapped[str | None] = mapped_column(String(120))
    adherence: Mapped[str | None] = mapped_column(String(120))


class Problem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "problems"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    code: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(String(255))
    since: Mapped[str | None] = mapped_column(String(40))


class LabResult(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lab_results"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    value: Mapped[str] = mapped_column(String(40))
    unit: Mapped[str] = mapped_column(String(40))
    reference_range: Mapped[str] = mapped_column(String(40))
    flag: Mapped[str | None] = mapped_column(String(2))
    collected_at: Mapped[date] = mapped_column(Date)


class Vital(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "vitals"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(40))
    value: Mapped[str] = mapped_column(String(40))


class Encounter(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "encounters"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), unique=True)
    type: Mapped[str] = mapped_column(String(80))
    date: Mapped[date] = mapped_column(Date)


class ClinicalNote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clinical_notes"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    encounter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("encounters.id"))
    template_id: Mapped[str] = mapped_column(String(40))
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    discipline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disciplines.id"))
    mode: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    diagnoses: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    routed_to_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cosigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cosigned_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    author: Mapped[User] = relationship(foreign_keys=[author_id], lazy="selectin")
    discipline: Mapped["Discipline"] = relationship(lazy="selectin")
    cosigned_by: Mapped[User | None] = relationship(foreign_keys=[cosigned_by_id], lazy="selectin")
    feedback: Mapped[list["NoteComment"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    addenda: Mapped[list["NoteAddendum"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class NoteComment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "note_comments"

    note_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinical_notes.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    author: Mapped[User] = relationship(lazy="selectin")


class NoteAddendum(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "note_addenda"

    note_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinical_notes.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    author: Mapped[User] = relationship(lazy="selectin")


class Appointment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "appointments"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    when: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    kind: Mapped[str] = mapped_column(String(120))
    with_whom: Mapped[str] = mapped_column(String(120))


class Referral(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "referrals"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    to_discipline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disciplines.id"))
    reason: Mapped[str] = mapped_column(Text)
    urgency: Mapped[str] = mapped_column(String(20))
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    to_discipline: Mapped["Discipline"] = relationship(lazy="selectin")
    created_by: Mapped[User] = relationship(lazy="selectin")
