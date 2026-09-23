# Import every model here so Alembic autogenerate can see them.
from app.models.audit import AuditEvent  # noqa: F401
from app.models.course import Course, Enrollment  # noqa: F401
from app.models.note import ClinicalNote  # noqa: F401
from app.models.patient import Patient  # noqa: F401
from app.models.scheduling import Appointment, Referral  # noqa: F401
from app.models.user import Discipline, Permission, Role, User  # noqa: F401
