from app.schemas.common import APIModel


class CourseReportOut(APIModel):
    course_id: str
    students_enrolled: int
    notes_by_status: dict[str, int]
    patients_by_mode: dict[str, int]
    audit_event_count: int
    audit_events_by_action: dict[str, int]