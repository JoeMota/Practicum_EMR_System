"""Sim Center lab check-in endpoints."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, Request, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.clinical import SimLabAssignmentOut, SimLabAssignmentWrite, SimLabRoomOut
from app.services.access import full_name, memberships_for, require, require_course
from app.services.audit import log_event
from app.services import sim_lab as lab

router = APIRouter(prefix="/courses/{course_id}/sim-lab", tags=["sim-lab"])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _room_out(room) -> SimLabRoomOut:
    return SimLabRoomOut(
        id=room.id,
        number=room.number,
        label=room.label,
        kind=room.kind,
        bed_count=room.bed_count,
        timing=room.timing,
        sort_order=room.sort_order,
        map_x=room.map_x,
        map_y=room.map_y,
        map_w=room.map_w,
        map_h=room.map_h,
        soft_capacity=lab.soft_capacity(room),
        bed_options=lab.bed_options(room.bed_count),
    )


def _assignment_out(row) -> SimLabAssignmentOut:
    return SimLabAssignmentOut(
        id=row.id,
        course_id=row.course_id,
        user_id=row.user_id,
        student_name=full_name(row.user),
        room=_room_out(row.room),
        session_date=row.session_date,
        bed=row.bed,
        role_label=row.role_label,
        time_block=row.time_block,
        assigned_by_name=full_name(row.assigned_by),
        created_at=row.created_at,
    )


@router.get("/rooms", response_model=list[SimLabRoomOut], response_model_exclude_none=True)
async def get_rooms(
    course_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    role: Annotated[str, Query()],
):
    rows = await memberships_for(db, user.id)
    require_course(role, course_id, user, rows)
    return [_room_out(room) for room in await lab.list_rooms(db)]


@router.get("/assignments", response_model=list[SimLabAssignmentOut], response_model_exclude_none=True)
async def get_assignments(
    course_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    role: Annotated[str, Query()],
    session_date: Annotated[date, Query()],
):
    rows = await memberships_for(db, user.id)
    require_course(role, course_id, user, rows)
    require(role, "case:author", "Only instructors can view the full lab board.")
    assignments = await lab.active_assignments(db, course_id=course_id, session_date=session_date)
    return [_assignment_out(row) for row in assignments]


@router.get("/mine", response_model=list[SimLabAssignmentOut], response_model_exclude_none=True)
async def get_mine(
    course_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    role: Annotated[str, Query()],
    session_date: Annotated[date | None, Query()] = None,
):
    rows = await memberships_for(db, user.id)
    require_course(role, course_id, user, rows)
    day = session_date or date.today()
    assignments = await lab.active_assignments(
        db, course_id=course_id, session_date=day, user_id=user.id
    )
    return [_assignment_out(row) for row in assignments]


@router.post(
    "/assignments",
    response_model=SimLabAssignmentOut,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
)
async def create_assignment(
    course_id: uuid.UUID,
    body: SimLabAssignmentWrite,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    rows = await memberships_for(db, user.id)
    require_course(role, course_id, user, rows)
    require(role, "case:author", "Only instructors can check students into rooms.")
    row = await lab.assign_student(
        db,
        course_id=course_id,
        user_id=body.user_id,
        room_id=body.room_id,
        session_date=body.session_date,
        assigned_by=user,
        bed=body.bed,
        role_label=body.role_label,
        time_block=body.time_block,
    )
    await log_event(
        db,
        action="sim_lab.assign",
        entity_type="sim_lab_assignment",
        entity_id=str(row.id),
        course_id=course_id,
        actor_user_id=user.id,
        ip_address=_ip(request),
        detail=f"room={row.room.number}",
    )
    await db.commit()
    return _assignment_out(row)


@router.post(
    "/assignments/{assignment_id}/clear",
    response_model=SimLabAssignmentOut,
    response_model_exclude_none=True,
)
async def clear_assignment(
    course_id: uuid.UUID,
    assignment_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    rows = await memberships_for(db, user.id)
    require_course(role, course_id, user, rows)
    require(role, "case:author", "Only instructors can clear lab assignments.")
    row = await lab.clear_assignment(db, assignment_id, course_id)
    await log_event(
        db,
        action="sim_lab.clear",
        entity_type="sim_lab_assignment",
        entity_id=str(assignment_id),
        course_id=course_id,
        actor_user_id=user.id,
        ip_address=_ip(request),
        detail=f"room={row.room.number}",
    )
    await db.commit()
    return _assignment_out(row)
