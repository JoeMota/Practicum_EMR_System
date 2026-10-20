import csv
import io
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import CurrentUser, DbSession
from app.models.clinical import Course
from app.schemas.reports import CourseReportOut
from app.services.access import memberships_for, require, require_held_role
from app.services.reports import course_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/courses/{course_id}", response_model=CourseReportOut)
async def get_course_report(
    course_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    format: Annotated[Literal["json", "csv"], Query()] = "json",
):
    rows = await memberships_for(db, user.id)
    require_held_role(user, "admin", rows)
    require("admin", "report:run", "Your role can't run reports.")
    if await db.get(Course, course_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found.")
    report = await course_report(db, course_id)
    if format == "json":
        return report

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(("category", "item", "count"))
    writer.writerow(("enrollment", "students", report["students_enrolled"]))
    for category, key in (("notes", "notes_by_status"), ("patients", "patients_by_mode"), ("audit_events", "audit_events_by_action")):
        writer.writerows((category, item, count) for item, count in report[key].items())
    writer.writerow(("audit_events", "total", report["audit_event_count"]))
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="course-{course_id}-report.csv"'},
    )