from datetime import datetime

from app.schemas.common import APIModel


class ActivityRow(APIModel):
    user_id: str
    student: str
    last_sign_in: datetime | None = None
    sessions: int
    active_minutes: float
    charts_opened: int
    notes_started: int
    notes_submitted: int


class ActivityReport(APIModel):
    rows: list[ActivityRow]


class AtRiskStudent(APIModel):
    user_id: str
    student: str
    reasons: list[str]


class AtRiskOut(APIModel):
    days: int
    students: list[AtRiskStudent]


class CourseReportOut(APIModel):
    course_id: str
    students_enrolled: int
    notes_by_status: dict[str, int]
    patients_by_mode: dict[str, int]
    audit_event_count: int
    audit_events_by_action: dict[str, int]