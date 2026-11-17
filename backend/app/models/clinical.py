import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.clinical_sections import DEFAULT_SECTION_LOCKS
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
    inactivity_days: Mapped[int] = mapped_column(Integer, default=7, server_default="7")
    rubric_file_name: Mapped[str | None] = mapped_column(String(255))
    grading_guide: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    guardrail_profile: Mapped[str] = mapped_column(String(30), default="practicum", server_default="practicum")
    guardrail_mode: Mapped[str | None] = mapped_column(String(20))
    ai_assist: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class CourseMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "course_memberships"
    __table_args__ = (UniqueConstraint("user_id", "course_id", "role_id", name="uq_membership_user_course_role"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    discipline_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("disciplines.id"))
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deactivated_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    user: Mapped[User] = relationship(back_populates="memberships", foreign_keys=[user_id])
    deactivated_by: Mapped[User | None] = relationship(foreign_keys=[deactivated_by_id])
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
    simulation_phase: Mapped[str | None] = mapped_column(String(20))
    case_key: Mapped[str] = mapped_column(String(50))
    source_patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patients.id"))
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    practice_label: Mapped[str | None] = mapped_column(String(80))
    chief_complaint: Mapped[str] = mapped_column(Text)
    hpi: Mapped[str] = mapped_column(Text)
    lifecycle: Mapped[str] = mapped_column(String(40))
    encounter_status: Mapped[str] = mapped_column(String(40))
    care_setting: Mapped[str] = mapped_column(String(40))
    program: Mapped[str | None] = mapped_column(String(80))
    past_medical_history: Mapped[str] = mapped_column(Text, default="", server_default="")
    family_history: Mapped[str] = mapped_column(Text, default="")
    surgical_history: Mapped[str] = mapped_column(Text, default="")
    social_history: Mapped[str] = mapped_column(Text, default="")
    insurance_payer: Mapped[str | None] = mapped_column(String(120))
    insurance_member_id: Mapped[str | None] = mapped_column(String(60))
    insurance_group_number: Mapped[str | None] = mapped_column(String(60))
    insurance_notes: Mapped[str | None] = mapped_column(Text)
    photo: Mapped[bytes | None] = mapped_column(LargeBinary)
    photo_content_type: Mapped[str | None] = mapped_column(String(40))
    emergency_contact_name: Mapped[str | None] = mapped_column(String(120))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(40))
    emergency_contact_relationship: Mapped[str | None] = mapped_column(String(60))
    code_status: Mapped[str | None] = mapped_column(String(40))
    advance_directive_notes: Mapped[str | None] = mapped_column(Text)
    hipaa_on_file: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    hipaa_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hipaa_note: Mapped[str | None] = mapped_column(Text)
    is_training: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    answer_key_released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    section_locks: Mapped[dict[str, Any]] = mapped_column(JSONB, default=lambda: dict(DEFAULT_SECTION_LOCKS))
    prefill_sections: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    grading_guide: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    planted_triggers: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    unit: Mapped[str | None] = mapped_column(String(80))
    room: Mapped[str | None] = mapped_column(String(40))
    bed: Mapped[str | None] = mapped_column(String(40))

    owner: Mapped[User | None] = relationship(foreign_keys=[owner_id], lazy="selectin")
    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_id], lazy="selectin")
    allergies: Mapped[list["Allergy"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    medications: Mapped[list["Medication"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    problems: Mapped[list["Problem"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    labs: Mapped[list["LabResult"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    vitals: Mapped[list["Vital"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    lung_sounds: Mapped[list["LungSound"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    encounter: Mapped["Encounter | None"] = relationship(
        cascade="all, delete-orphan", lazy="selectin", uselist=False
    )


class PatientIntake(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "patient_intakes"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), unique=True, index=True
    )
    data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class Allergy(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "allergies"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    substance: Mapped[str] = mapped_column(String(120))
    reaction: Mapped[str | None] = mapped_column(String(120))
    severity: Mapped[str | None] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(20), default="medication", server_default="medication")


class Medication(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "medications"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    dose: Mapped[str] = mapped_column(String(60))
    route: Mapped[str] = mapped_column(String(40))
    frequency: Mapped[str] = mapped_column(String(80))
    indication: Mapped[str | None] = mapped_column(String(120))
    adherence: Mapped[str | None] = mapped_column(String(120))
    access_cost: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    discontinued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    prescribed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_compound: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    compound_ingredients: Mapped[str | None] = mapped_column(Text)
    compound_vehicle: Mapped[str | None] = mapped_column(String(120))
    compound_reason: Mapped[str | None] = mapped_column(Text)
    rxcui: Mapped[str | None] = mapped_column(String(20))
    generic_name: Mapped[str | None] = mapped_column(String(120))
    brand_names: Mapped[list[Any]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    flags: Mapped[list[Any]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))


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
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_by_name: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="recorded", server_default="recorded")


class LungSound(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lung_sounds"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    location: Mapped[str] = mapped_column(String(20))
    finding: Mapped[str] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_by_name: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="recorded", server_default="recorded")


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
    sensitive: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    sensitivity: Mapped[str] = mapped_column(String(20), default="standard", server_default="standard")
    content_cipher: Mapped[str | None] = mapped_column(Text)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    discipline_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("disciplines.id"))
    mode: Mapped[str] = mapped_column(String(20))
    kind: Mapped[str] = mapped_column(String(20), default="visit", server_default="visit")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    diagnoses: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    routed_to_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    cpt_codes: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    rubric_scores: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    body_locked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
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
    body_cipher: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20))
    section_id: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    author: Mapped[User] = relationship(lazy="selectin")


class NoteAddendum(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "note_addenda"

    note_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinical_notes.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    body_cipher: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    author: Mapped[User] = relationship(lazy="selectin")


class SavedNoteTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "note_templates"

    name: Mapped[str] = mapped_column(String(120))
    discipline: Mapped[str] = mapped_column(String(40))
    course_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("courses.id"), index=True)
    sensitive: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    sensitivity: Mapped[str] = mapped_column(String(20), default="standard", server_default="standard")
    sections: Mapped[list[Any]] = mapped_column(JSONB)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class Appointment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "appointments"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    when: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    kind: Mapped[str] = mapped_column(String(120))
    with_whom: Mapped[str] = mapped_column(String(120))


class CaseAnswerKey(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One shared key per case master. Read live from the master; never copied onto a student chart."""

    __tablename__ = "case_answer_keys"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), unique=True)
    diagnoses: Mapped[list[Any]] = mapped_column(JSONB)
    expected_cpt_codes: Mapped[list[Any]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"), nullable=False)
    plan_points: Mapped[list[Any]] = mapped_column(JSONB)
    rationale: Mapped[str] = mapped_column(Text, default="", server_default="")
    updated_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    updated_by: Mapped[User] = relationship(lazy="selectin")


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


class SimulationAssignment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "simulation_assignments"
    __table_args__ = (UniqueConstraint("patient_id", "user_id", name="uq_simulation_patient_user"),)

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    station: Mapped[str] = mapped_column(String(20))

    user: Mapped[User] = relationship(lazy="selectin")


class ChartSession(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "chart_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MedicationAdministration(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "medication_administrations"

    medication_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medications.id", ondelete="CASCADE"), index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    dose_given: Mapped[str] = mapped_column(String(80))
    administered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    review_status: Mapped[str] = mapped_column(String(20), default="pending_review", server_default="pending_review")
    review_comment: Mapped[str | None] = mapped_column(Text)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    medication: Mapped[Medication] = relationship(lazy="selectin")
    student: Mapped[User] = relationship(foreign_keys=[student_id], lazy="selectin")
    reviewed_by: Mapped[User | None] = relationship(foreign_keys=[reviewed_by_id], lazy="selectin")


class MedicationOrder(UUIDPrimaryKeyMixin, Base):
    """Teaching fill: student/tech submits → pharmacist verifies or holds → optional release."""

    __tablename__ = "medication_orders"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    medication_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medications.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    dose: Mapped[str] = mapped_column(String(60))
    route: Mapped[str] = mapped_column(String(40))
    frequency: Mapped[str] = mapped_column(String(80))
    quantity: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default="pending_verify", server_default="pending_verify")
    submitted_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_comment: Mapped[str | None] = mapped_column(Text)

    medication: Mapped[Medication] = relationship(lazy="selectin")
    submitted_by: Mapped[User] = relationship(foreign_keys=[submitted_by_id], lazy="selectin")
    reviewed_by: Mapped[User | None] = relationship(foreign_keys=[reviewed_by_id], lazy="selectin")


class SimLabRoom(UUIDPrimaryKeyMixin, Base):
    """UTEP Sim Center room catalog for lab check-in (assignable rooms only)."""

    __tablename__ = "sim_lab_rooms"

    number: Mapped[str] = mapped_column(String(20), unique=True)
    label: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(20))  # ward | big_lab | testing | exam
    bed_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    timing: Mapped[str] = mapped_column(String(20), default="day", server_default="day")  # day | hour
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    map_x: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    map_y: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    map_w: Mapped[int] = mapped_column(Integer, default=10, server_default="10")
    map_h: Mapped[int] = mapped_column(Integer, default=10, server_default="10")


class SimLabAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Instructor check-in: student → room (bed/role/block optional)."""

    __tablename__ = "sim_lab_assignments"

    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sim_lab_rooms.id", ondelete="RESTRICT"), index=True)
    session_date: Mapped[date] = mapped_column(Date, index=True)
    bed: Mapped[str | None] = mapped_column(String(8))
    role_label: Mapped[str | None] = mapped_column(String(40))
    time_block: Mapped[str | None] = mapped_column(String(40))
    assigned_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    room: Mapped[SimLabRoom] = relationship(lazy="selectin")
    user: Mapped[User] = relationship(foreign_keys=[user_id], lazy="selectin")
    assigned_by: Mapped[User] = relationship(foreign_keys=[assigned_by_id], lazy="selectin")
