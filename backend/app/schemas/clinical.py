import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import APIModel

DisciplineCode = Literal[
    "pharmacy", "physical_therapy", "occupational_therapy", "speech_language_pathology", "nursing"
]
NoteTemplate = Literal["pharmacy_mtm", "pt_daily_soap", "general_soap"]
RoleCode = Literal["student", "instructor", "admin", "front_desk", "patient"]
CourseStatus = Literal["planned", "active", "ended", "archived"]


class RoleAssignmentOut(APIModel):
    role: str
    discipline: str | None = None
    course_ids: list[str]


class PublicUser(APIModel):
    id: str
    full_name: str
    email: str
    university_id: str | None = None
    phone_last4: str | None = None
    must_change_password: bool = False
    is_active: bool = True
    roles: list[RoleAssignmentOut]


class CourseOut(APIModel):
    id: str
    code: str
    title: str
    term: str
    status: CourseStatus
    instructor_ids: list[str]
    rubric_file_name: str | None = None


class CourseCreate(APIModel):
    code: str = Field(min_length=1, max_length=30)
    title: str = Field(min_length=1, max_length=200)
    term: str = Field(min_length=1, max_length=40)


class CourseStatusPatch(APIModel):
    status: CourseStatus


class AllergyOut(APIModel):
    substance: str
    reaction: str | None = None
    severity: str | None = None


class MedicationOut(APIModel):
    id: str
    name: str
    dose: str
    route: str
    frequency: str
    indication: str | None = None
    adherence: str | None = None


class ProblemOut(APIModel):
    code: str | None = None
    description: str
    since: str | None = None


class LabOut(APIModel):
    id: str
    name: str
    value: str
    unit: str
    reference_range: str
    flag: str | None = None
    collected_at: date


class VitalOut(APIModel):
    label: str
    value: str


class EncounterOut(APIModel):
    id: str
    type: str
    date: date


class StatusOut(APIModel):
    lifecycle: str
    encounter: str
    care_setting: str
    program: str | None = None


class InsuranceOut(APIModel):
    payer: str | None = None
    member_id: str | None = None
    group_number: str | None = None


class EmergencyContactOut(APIModel):
    name: str | None = None
    phone: str | None = None
    relationship: str | None = None


class PatientOut(APIModel):
    id: str
    mrn: str
    first_name: str
    last_name: str
    preferred_name: str | None = None
    dob: date
    age_years: int
    sex_at_birth: str
    pronouns: str | None = None
    course_id: str
    mode: str
    case_template_id: str
    source_patient_id: str | None = None
    owner_id: str | None = None
    owner_name: str | None = None
    is_training: bool
    practice_label: str | None = None
    chief_complaint: str
    hpi: str
    status: StatusOut
    allergies: list[AllergyOut]
    medications: list[MedicationOut]
    problems: list[ProblemOut]
    labs: list[LabOut]
    vitals: list[VitalOut]
    family_history: str
    surgical_history: str
    social_history: str
    encounter: EncounterOut
    insurance: InsuranceOut
    emergency_contact: EmergencyContactOut


class LatestNote(APIModel):
    status: str
    updated_at: datetime


class PatientRowOut(APIModel):
    patient: PatientOut
    owner_name: str | None = None
    latest_note: LatestNote | None = None


class StatusPatch(APIModel):
    lifecycle: str | None = None
    encounter: str | None = None
    care_setting: str | None = None
    program: str | None = None


class AssignCase(APIModel):
    source_patient_id: uuid.UUID
    owner_id: uuid.UUID


class IcdCode(APIModel):
    code: str
    label: str


class NoteCommentOut(APIModel):
    id: str
    author_id: str
    author_name: str
    body: str
    kind: str
    created_at: datetime


class AddendumOut(APIModel):
    id: str
    author_name: str
    body: str
    created_at: datetime


class NoteOut(APIModel):
    id: str
    patient_id: str
    encounter_id: str
    template_id: str
    author_id: str
    author_name: str
    author_discipline: str
    mode: str
    status: str
    version: int
    content: dict[str, str]
    diagnoses: list[IcdCode]
    routed_to_id: str | None = None
    created_at: datetime
    updated_at: datetime
    signed_at: datetime | None = None
    cosigned_at: datetime | None = None
    cosigned_by_name: str | None = None
    feedback: list[NoteCommentOut]
    addenda: list[AddendumOut]


class DraftCreate(APIModel):
    template_id: NoteTemplate
    discipline: DisciplineCode


class DraftPatch(APIModel):
    expected_version: int
    template_id: NoteTemplate | None = None
    content: dict[str, str] | None = None
    diagnoses: list[IcdCode] | None = None
    routed_to_id: uuid.UUID | None = None


class SignRequest(APIModel):
    expected_version: int


class CommentBody(APIModel):
    comment: str = ""


class AddendumBody(APIModel):
    body: str = Field(min_length=1)


class QueueItemOut(APIModel):
    note: NoteOut
    patient: PatientOut


class AppointmentOut(APIModel):
    id: str
    patient_id: str
    when: datetime
    kind: str
    with_whom: str


class ReferralOut(APIModel):
    id: str
    patient_id: str
    to_discipline: str
    reason: str
    urgency: str
    created_by_name: str
    created_at: datetime


class ReferralCreate(APIModel):
    to_discipline: DisciplineCode
    reason: str = Field(min_length=1)
    urgency: Literal["routine", "urgent"]


class RosterRowIn(APIModel):
    full_name: str
    email: str
    university_id: str
    problem: str | None = None


class RosterImport(APIModel):
    discipline: DisciplineCode
    rows: list[RosterRowIn]
    role: Literal["student", "instructor"] = "student"


class TempPassword(APIModel):
    email: str
    password: str


class RosterImportResult(APIModel):
    added: int
    already_enrolled: int
    temporary_passwords: list[TempPassword] = []


class AuditOut(APIModel):
    id: str
    timestamp: datetime
    actor_id: str
    actor_name: str
    action: str
    entity: str
    result: str
    detail: str | None = None
