import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import APIModel

DisciplineCode = Literal[
    "pharmacy", "physical_therapy", "occupational_therapy", "speech_language_pathology", "nursing"
]
NoteTemplate = Literal[
    "pharmacy_soap", "sbar", "phone_note", "telehealth_visit", "pharmacy_mtm", "pt_daily_soap", "general_soap"
]
RoleCode = Literal["student", "instructor", "course_coordinator", "admin", "front_desk", "patient"]
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
    archived_at: datetime | None = None
    roles: list[RoleAssignmentOut]
    roster_status: Literal["active", "inactive"] | None = None
    deactivated_at: datetime | None = None


class CourseOut(APIModel):
    id: str
    code: str
    title: str
    term: str
    status: CourseStatus
    inactivity_days: int = 7
    instructor_ids: list[str]
    rubric_file_name: str | None = None
    grading_guide: dict | None = None
    guardrail_profile: str = "practicum"
    guardrail_mode: str | None = None
    ai_assist: bool = False
    ai_provider_configured: bool = False


class CourseCreate(APIModel):
    code: str = Field(min_length=1, max_length=30)
    title: str = Field(min_length=1, max_length=200)
    term: str = Field(min_length=1, max_length=40)


class CourseStatusPatch(APIModel):
    status: CourseStatus


class InactivityDaysPatch(APIModel):
    days: int = Field(ge=1, le=90)


class CoursePolicyPatch(APIModel):
    guardrail_profile: Literal["intro_pharmacy", "practicum", "clinical_other"] | None = None
    guardrail_mode: Literal["off", "advisory", "acknowledge", "block"] | None = None
    ai_assist: bool | None = None


class PresenceIn(APIModel):
    active: bool = False


class AllergyOut(APIModel):
    id: str | None = None
    substance: str
    reaction: str | None = None
    severity: str | None = None
    category: str = "medication"


class MedicationOut(APIModel):
    id: str
    name: str
    dose: str
    route: str
    frequency: str
    sig: str | None = None
    indication: str | None = None
    adherence: str | None = None
    access_cost: str | None = None
    status: str = "active"
    prescribed: bool = False
    is_compound: bool = False
    compound_ingredients: str | None = None
    compound_vehicle: str | None = None
    compound_reason: str | None = None
    discontinued_at: datetime | None = None
    rxcui: str | None = None
    generic_name: str | None = None
    brand_names: list[str] = Field(default_factory=list)
    flags: list[dict] = Field(default_factory=list)


class ProblemOut(APIModel):
    id: str | None = None
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
    id: str | None = None
    label: str
    value: str
    recorded_at: datetime | None = None
    recorded_by_name: str | None = None
    status: str = "recorded"


class LungSoundOut(APIModel):
    id: str | None = None
    location: str
    finding: str
    notes: str | None = None
    recorded_at: datetime | None = None
    recorded_by_name: str | None = None
    status: str = "recorded"


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
    notes: str | None = None


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
    past_medical_history: str = ""
    status: StatusOut
    allergies: list[AllergyOut]
    medications: list[MedicationOut]
    problems: list[ProblemOut]
    labs: list[LabOut]
    vitals: list[VitalOut]
    lung_sounds: list[LungSoundOut] = []
    family_history: str
    surgical_history: str
    social_history: str
    encounter: EncounterOut
    insurance: InsuranceOut
    emergency_contact: EmergencyContactOut
    code_status: str | None = None
    advance_directive_notes: str | None = None
    hipaa_on_file: bool = False
    hipaa_signed_at: datetime | None = None
    hipaa_note: str | None = None
    section_locks: dict[str, bool] = {}
    prefill_sections: list[str] = []
    unit: str | None = None
    room: str | None = None
    bed: str | None = None
    has_photo: bool = False
    simulation_phase: str | None = None
    viewer_station: str | None = None


class LatestNote(APIModel):
    status: str
    updated_at: datetime


class PatientRowOut(APIModel):
    patient: PatientOut
    owner_name: str | None = None
    latest_note: LatestNote | None = None
    open_flag_count: int = 0


class StatusPatch(APIModel):
    lifecycle: str | None = None
    encounter: str | None = None
    care_setting: str | None = None
    program: str | None = None


class AssignCase(APIModel):
    source_patient_id: uuid.UUID
    owner_id: uuid.UUID


class StartSimulation(APIModel):
    nurse_id: uuid.UUID
    pharmacist_id: uuid.UUID | None = None
    provider_id: uuid.UUID | None = None


class ChartPresence(APIModel):
    user_id: str
    name: str
    station: str | None = None
    last_seen_at: datetime


class IcdCode(APIModel):
    code: str
    label: str
    rationale: str = ""


class ExpectedCptCode(APIModel):
    code: str
    label: str


class CptSelection(APIModel):
    code: str
    label: str
    diagnosis_codes: list[str] = Field(default_factory=list)


class NoteCommentOut(APIModel):
    id: str
    author_id: str
    author_name: str
    body: str
    kind: str
    section_id: str | None = None
    created_at: datetime


class SectionCommentIn(APIModel):
    section_id: str | None = Field(default=None, max_length=10)
    body: str = Field(min_length=1)


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
    kind: str = "visit"
    status: str
    version: int
    content: dict[str, str]
    diagnoses: list[IcdCode]
    cpt_codes: list[CptSelection] = Field(default_factory=list)
    body_locked: bool = False
    sensitivity: str = "standard"
    rubric_scores: dict | None = None
    routed_to_id: str | None = None
    created_at: datetime
    updated_at: datetime
    signed_at: datetime | None = None
    cosigned_at: datetime | None = None
    cosigned_by_name: str | None = None
    feedback: list[NoteCommentOut]
    addenda: list[AddendumOut]


class DraftCreate(APIModel):
    template_id: str = Field(min_length=1, max_length=40)
    discipline: DisciplineCode
    kind: Literal["visit", "clarification"] = "visit"


class DraftPatch(APIModel):
    expected_version: int
    template_id: str | None = Field(default=None, max_length=40)
    content: dict[str, str] | None = None
    diagnoses: list[IcdCode] | None = None
    cpt_codes: list[CptSelection] | None = None
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
    role: Literal["student", "instructor", "course_coordinator"] = "student"


class TempPassword(APIModel):
    email: str
    password: str


class RosterImportResult(APIModel):
    added: int
    already_enrolled: int
    reactivated: int = 0
    temporary_passwords: list[TempPassword] = []


class EnrollmentCreate(APIModel):
    user_id: uuid.UUID
    role: Literal["student", "instructor", "course_coordinator"]
    discipline: DisciplineCode


class CaseAllergyIn(APIModel):
    substance: str = ""
    reaction: str | None = None
    severity: str | None = None
    category: str | None = None


class CaseMedicationIn(APIModel):
    name: str = ""
    dose: str = ""
    route: str = ""
    frequency: str = ""
    indication: str | None = None
    adherence: str | None = None
    access_cost: str | None = None
    prescribed: bool = False
    is_compound: bool = False
    compound_ingredients: str | None = None
    compound_vehicle: str | None = None
    compound_reason: str | None = None


class CaseProblemIn(APIModel):
    code: str | None = None
    description: str = ""
    since: str | None = None


class CaseLabIn(APIModel):
    name: str = ""
    value: str = ""
    unit: str = ""
    reference_range: str = ""
    flag: str | None = None
    collected_at: date | None = None


class CaseVitalIn(APIModel):
    label: str = ""
    value: str = ""


class CaseLungSoundIn(APIModel):
    location: str = ""
    finding: str = ""
    notes: str | None = None


class CaseIn(APIModel):
    first_name: str
    last_name: str
    preferred_name: str | None = None
    dob: date
    sex_at_birth: str
    pronouns: str | None = None
    chief_complaint: str = ""
    hpi: str = ""
    past_medical_history: str = ""
    surgical_history: str = ""
    family_history: str = ""
    social_history: str = ""
    insurance_payer: str | None = None
    insurance_member_id: str | None = None
    insurance_group_number: str | None = None
    insurance_notes: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    emergency_contact_relationship: str | None = None
    code_status: str | None = None
    advance_directive_notes: str | None = None
    hipaa_on_file: bool = False
    hipaa_note: str | None = None
    encounter_type: str = "Office visit"
    care_setting: str = "Outpatient"
    lifecycle: str = "Active"
    encounter_status: str = "Scheduled"
    program: str | None = None
    allergies: list[CaseAllergyIn] = []
    medications: list[CaseMedicationIn] = []
    problems: list[CaseProblemIn] = []
    labs: list[CaseLabIn] = []
    vitals: list[CaseVitalIn] = []
    lung_sounds: list[CaseLungSoundIn] = []
    section_locks: dict[str, bool] | None = None
    prefill_sections: list[str] | None = None
    unit: str | None = None
    room: str | None = None
    bed: str | None = None


class PlantedTrigger(APIModel):
    finding: str = ""
    explanation: str = ""


class CaseOut(PatientOut):
    created_by_name: str | None = None
    updated_at: datetime
    grading_guide: dict | None = None
    triggers: list[PlantedTrigger] = []


class TriggersIn(APIModel):
    triggers: list[PlantedTrigger] = []


class TriggersOut(APIModel):
    triggers: list[PlantedTrigger] = []


class CaseCopyIn(APIModel):
    course_id: uuid.UUID


class AnswerDiagnosis(APIModel):
    rank: int = 0
    code: str = ""
    label: str = ""
    rationale: str = ""


class AnswerKeyIn(APIModel):
    diagnoses: list[AnswerDiagnosis] = []
    expected_cpt_codes: list[ExpectedCptCode] = Field(default_factory=list)
    plan_points: list[str] = []
    rationale: str = ""


class AnswerKeyOut(APIModel):
    diagnoses: list[AnswerDiagnosis] = []
    expected_cpt_codes: list[ExpectedCptCode] = Field(default_factory=list)
    plan_points: list[str] = []
    rationale: str = ""
    updated_at: datetime | None = None


class AuditOut(APIModel):
    id: str
    timestamp: datetime
    actor_id: str
    actor_name: str
    action: str
    entity: str
    result: str
    detail: str | None = None


class AllergyWrite(APIModel):
    substance: str = ""
    reaction: str | None = None
    severity: str | None = None
    category: str = "medication"


class MedicationWrite(APIModel):
    name: str = ""
    dose: str = ""
    route: str = ""
    frequency: str = ""
    indication: str | None = None
    adherence: str | None = None
    access_cost: str | None = None
    prescribed: bool = False
    is_compound: bool = False
    compound_ingredients: str | None = None
    compound_vehicle: str | None = None
    compound_reason: str | None = None
    rxcui: str | None = None
    generic_name: str | None = None
    brand_names: list[str] = Field(default_factory=list)
    acknowledged_flags: list[str] = Field(default_factory=list)
    clear_flags: bool = False


class SuggestIn(APIModel):
    section_id: str = Field(min_length=1, max_length=40)


class DoseCheckIn(APIModel):
    text: str = Field(default="", max_length=20000)
    acknowledged_flags: list[str] = Field(default_factory=list)


class DoseFlagOut(APIModel):
    code: str
    message: str


class DoseCheckOut(APIModel):
    flags: list[DoseFlagOut]
    blocked: bool = False
    needs_acknowledgement: bool = False


class VitalWrite(APIModel):
    label: str
    value: str


class LungSoundWrite(APIModel):
    location: str
    finding: str
    notes: str | None = None


class LabWrite(APIModel):
    name: str
    value: str = ""
    unit: str = ""
    reference_range: str = ""
    flag: str | None = None
    collected_at: date


class ProblemWrite(APIModel):
    code: str | None = None
    description: str
    since: str | None = None


class HistoryWrite(APIModel):
    section: Literal["medical_history", "surgical_history", "chief_complaint"]
    value: str = ""


class PlacementWrite(APIModel):
    unit: str | None = None
    room: str | None = None
    bed: str | None = None


class AdministerWrite(APIModel):
    dose_given: str = ""


class AdministrationReview(APIModel):
    decision: Literal["accepted", "needs_follow_up"]
    comment: str = ""


class MedicationOrderCreate(APIModel):
    medication_id: uuid.UUID
    quantity: str | None = None


class MedicationOrderReview(APIModel):
    decision: Literal["verify", "hold", "release", "resubmit"]
    comment: str = ""


class MedicationOrderOut(APIModel):
    id: str
    medication_id: str
    name: str
    dose: str
    route: str
    frequency: str
    sig: str | None = None
    quantity: str | None = None
    status: str
    submitted_by_name: str
    submitted_at: datetime
    reviewed_by_name: str | None = None
    reviewed_at: datetime | None = None
    review_comment: str | None = None
    is_compound: bool = False


class ScoreCriterion(APIModel):
    id: str
    score: float | None = None
    feedback: str = ""
    max_points: float | None = None


class ScoreWrite(APIModel):
    criteria: list[ScoreCriterion] = []
    overall_feedback: str = ""


class InstructorEdit(APIModel):
    content: dict[str, str] | None = None
    diagnoses: list[IcdCode] | None = None
    cpt_codes: list[CptSelection] | None = None


class PortalAccess(APIModel):
    email: str
    full_name: str
    patient_id: uuid.UUID


class PhotoIn(APIModel):
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    data: str = Field(min_length=1)


class PhotoOut(APIModel):
    content_type: str
    data: str


class TemplateFieldIn(APIModel):
    id: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=120)
    kind: Literal["text", "textarea", "icd10", "medrec"]


class TemplateSectionIn(APIModel):
    id: str = Field(min_length=1, max_length=10)
    title: str = Field(min_length=1, max_length=80)
    fields: list[TemplateFieldIn] = Field(min_length=1, max_length=12)


class NoteTemplateIn(APIModel):
    name: str = Field(min_length=1, max_length=120)
    discipline: DisciplineCode
    course_id: uuid.UUID | None = None
    sensitive: bool = False
    sensitivity: Literal["standard", "psychiatry", "protected"] | None = None
    sections: list[TemplateSectionIn] = Field(min_length=1, max_length=12)


class NoteTemplateOut(APIModel):
    id: str
    name: str
    discipline: str
    scope: Literal["shared", "course"]
    sensitive: bool = False
    sensitivity: str = "standard"
    sections: list[TemplateSectionIn]


class SimLabRoomOut(APIModel):
    id: uuid.UUID
    number: str
    label: str
    kind: str
    bed_count: int
    timing: str
    sort_order: int
    map_x: int
    map_y: int
    map_w: int
    map_h: int
    soft_capacity: int | None = None
    bed_options: list[str] = []


class SimLabAssignmentWrite(APIModel):
    user_id: uuid.UUID
    room_id: uuid.UUID
    session_date: date
    bed: str | None = None
    role_label: str | None = None
    time_block: str | None = None


class SimLabAssignmentOut(APIModel):
    id: uuid.UUID
    course_id: uuid.UUID
    user_id: uuid.UUID
    student_name: str
    room: SimLabRoomOut
    session_date: date
    bed: str | None = None
    role_label: str | None = None
    time_block: str | None = None
    assigned_by_name: str
    created_at: datetime
