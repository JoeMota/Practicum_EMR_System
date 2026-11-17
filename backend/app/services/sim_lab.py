"""Sim Center lab check-in: rooms + student assignments."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.clinical import CourseMembership, SimLabAssignment, SimLabRoom
from app.models.user import User

BED_LETTERS = "ABCDEFGHIJ"


def bed_options(bed_count: int) -> list[str]:
    return [BED_LETTERS[i] for i in range(min(bed_count, len(BED_LETTERS)))]


def soft_capacity(room: SimLabRoom) -> int | None:
    """Hint only — wards/big labs ≈ 5 students per bed; singles left open."""
    if room.kind in {"ward", "big_lab"}:
        return room.bed_count * 5
    return None


async def list_rooms(db: AsyncSession) -> list[SimLabRoom]:
    result = await db.scalars(select(SimLabRoom).order_by(SimLabRoom.sort_order, SimLabRoom.number))
    return list(result)


async def get_room(db: AsyncSession, room_id: uuid.UUID) -> SimLabRoom:
    room = await db.get(SimLabRoom, room_id)
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found.")
    return room


async def active_assignments(
    db: AsyncSession,
    *,
    course_id: uuid.UUID,
    session_date: date,
    user_id: uuid.UUID | None = None,
) -> list[SimLabAssignment]:
    stmt = (
        select(SimLabAssignment)
        .where(SimLabAssignment.course_id == course_id)
        .where(SimLabAssignment.session_date == session_date)
        .where(SimLabAssignment.cleared_at.is_(None))
        .options(
            selectinload(SimLabAssignment.room),
            selectinload(SimLabAssignment.user),
            selectinload(SimLabAssignment.assigned_by),
        )
        .order_by(SimLabAssignment.created_at)
    )
    if user_id is not None:
        stmt = stmt.where(SimLabAssignment.user_id == user_id)
    return list(await db.scalars(stmt))


async def ensure_student_in_course(db: AsyncSession, course_id: uuid.UUID, user_id: uuid.UUID) -> User:
    row = await db.scalar(
        select(CourseMembership)
        .where(CourseMembership.course_id == course_id)
        .where(CourseMembership.user_id == user_id)
        .where(CourseMembership.deactivated_at.is_(None))
        .options(selectinload(CourseMembership.role), selectinload(CourseMembership.user))
    )
    if not row or row.role.code != "student":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Pick a student on this course roster.")
    return row.user


async def assign_student(
    db: AsyncSession,
    *,
    course_id: uuid.UUID,
    user_id: uuid.UUID,
    room_id: uuid.UUID,
    session_date: date,
    assigned_by: User,
    bed: str | None = None,
    role_label: str | None = None,
    time_block: str | None = None,
) -> SimLabAssignment:
    await ensure_student_in_course(db, course_id, user_id)
    room = await get_room(db, room_id)

    bed_clean = (bed or "").strip().upper() or None
    if bed_clean:
        allowed = bed_options(room.bed_count)
        if bed_clean not in allowed:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"Bed must be one of {', '.join(allowed)} for room {room.number}.",
            )

    role_clean = (role_label or "").strip() or None
    block_clean = (time_block or "").strip() or None
    if room.timing == "day":
        block_clean = None

    existing = await db.scalar(
        select(SimLabAssignment)
        .where(SimLabAssignment.course_id == course_id)
        .where(SimLabAssignment.user_id == user_id)
        .where(SimLabAssignment.session_date == session_date)
        .where(SimLabAssignment.cleared_at.is_(None))
        .options(
            selectinload(SimLabAssignment.room),
            selectinload(SimLabAssignment.user),
            selectinload(SimLabAssignment.assigned_by),
        )
    )
    if existing:
        existing.room = room
        existing.bed = bed_clean
        existing.role_label = role_clean
        existing.time_block = block_clean
        existing.assigned_by_id = assigned_by.id
        existing.assigned_by = assigned_by
        await db.flush()
        return existing

    row = SimLabAssignment(
        course_id=course_id,
        user_id=user_id,
        room_id=room.id,
        session_date=session_date,
        bed=bed_clean,
        role_label=role_clean,
        time_block=block_clean,
        assigned_by_id=assigned_by.id,
    )
    db.add(row)
    await db.flush()
    loaded = await active_assignments(
        db, course_id=course_id, session_date=session_date, user_id=user_id
    )
    return loaded[0]


async def clear_assignment(db: AsyncSession, assignment_id: uuid.UUID, course_id: uuid.UUID) -> SimLabAssignment:
    row = await db.scalar(
        select(SimLabAssignment)
        .where(SimLabAssignment.id == assignment_id)
        .where(SimLabAssignment.course_id == course_id)
        .options(
            selectinload(SimLabAssignment.room),
            selectinload(SimLabAssignment.user),
            selectinload(SimLabAssignment.assigned_by),
        )
    )
    if not row or row.cleared_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found.")
    row.cleared_at = datetime.now(timezone.utc)
    await db.flush()
    return row
