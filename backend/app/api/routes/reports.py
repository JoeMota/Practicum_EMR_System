import csv
import io
import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.clinical import Course
from app.schemas.reports import ActivityReport, AtRiskOut, CourseReportOut
from app.services.access import can, memberships_for, require, require_course, require_held_role
from app.services.activity import activity_rows, at_risk, workbook_for
from app.services.reports import course_report
from app.services.teaching_exports import grade_workbook

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


async def _teaching(db, user, course_id, role: str) -> None:
    rows = await memberships_for(db, user.id)
    require_course(role, course_id, user, rows)
    if not can(role, "report:export_teaching"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role can't export teaching reports.")


@router.get("/courses/{course_id}/grades.xlsx")
async def export_grades(
    course_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    role: Annotated[str, Query()],
    case_key: Annotated[str, Query()],
):
    await _teaching(db, user, course_id, role)
    if await db.get(Course, course_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found.")
    payload = await grade_workbook(db, course_id, case_key)
    return Response(
        payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="case-grades.xlsx"'},
    )


@router.get("/courses/{course_id}/activity", response_model=ActivityReport)
async def course_activity(
    course_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    role: Annotated[str, Query()],
    start: Annotated[date, Query()],
    end: Annotated[date, Query()],
):
    await _teaching(db, user, course_id, role)
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found.")
    return {"rows": await activity_rows(db, course_id, start, end)}


@router.get("/courses/{course_id}/activity.xlsx")
async def export_activity(
    course_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    role: Annotated[str, Query()],
    start: Annotated[date, Query()],
    end: Annotated[date, Query()],
):
    await _teaching(db, user, course_id, role)
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found.")
    payload = workbook_for([(course.code, await activity_rows(db, course_id, start, end))])
    return Response(
        payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="student-activity.xlsx"'},
    )


@router.get("/activity.xlsx")
async def export_all_activity(
    db: DbSession,
    user: CurrentUser,
    start: Annotated[date, Query()],
    end: Annotated[date, Query()],
):
    rows = await memberships_for(db, user.id)
    require_held_role(user, "admin", rows)
    require("admin", "report:run", "Your role can't export every course.")
    courses = list((await db.scalars(select(Course).order_by(Course.code))).all())
    payload = workbook_for([(course.code, await activity_rows(db, course.id, start, end)) for course in courses])
    return Response(
        payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="student-activity.xlsx"'},
    )


@router.get("/courses/{course_id}/at-risk", response_model=AtRiskOut)
async def course_at_risk(
    course_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    role: Annotated[str, Query()],
):
    await _teaching(db, user, course_id, role)
    return await at_risk(db, course_id)