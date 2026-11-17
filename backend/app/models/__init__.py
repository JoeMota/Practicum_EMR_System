# Import every model here so Alembic autogenerate can see them.
from app.models.audit import AuditEvent  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.clinical import (  # noqa: F401
    Allergy,
    Appointment,
    CaseAnswerKey,
    ClinicalNote,
    Course,
    CourseMembership,
    Encounter,
    LabResult,
    ChartSession,
    Medication,
    MedicationAdministration,
    MedicationOrder,
    NoteAddendum,
    NoteComment,
    Patient,
    PatientIntake,
    Problem,
    SavedNoteTemplate,
    Referral,
    SimulationAssignment,
    SimLabAssignment,
    SimLabRoom,
    Vital,
)
from app.models.user import Discipline, Permission, Role, User  # noqa: F401
