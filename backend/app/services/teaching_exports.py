"""Instructor Excel exports. Case charts themselves are not included."""

import io
import uuid

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinical import ClinicalNote, Patient
from app.services.access import full_name


def _sheet_bytes(book: Workbook) -> bytes:
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


async def grade_workbook(db: AsyncSession, course_id: uuid.UUID, case_key: str) -> bytes:
    patients = list(
        (
            await db.scalars(
                select(Patient).where(
                    Patient.course_id == course_id,
                    Patient.case_key == case_key,
                    Patient.mode == "assessment",
                    Patient.deleted_at.is_(None),
                )
            )
        ).all()
    )
    book = Workbook()
    summary = book.active
    summary.title = "Score bands"
    summary.append(["Band", "Students"])
    bands = {"Below 70": 0, "70s": 0, "80s": 0, "90 and above": 0, "Not scored": 0}
    detail = book.create_sheet("Students")
    detail.append(["Student", "Score", "Points possible", "Percent"])
    for patient in patients:
        note = await db.scalar(
            select(ClinicalNote)
            .where(
                ClinicalNote.patient_id == patient.id,
                ClinicalNote.archived.is_(False),
                ClinicalNote.mode == "assessment",
            )
            .order_by(ClinicalNote.updated_at.desc())
        )
        student = full_name(patient.owner) if patient.owner else ""
        score, possible = _score(note.rubric_scores if note else None)
        if possible <= 0 or score is None:
            bands["Not scored"] += 1
            detail.append([student, score if score is not None else "", possible or "", ""])
            continue
        percent = round(100 * score / possible)
        if percent >= 90:
            bands["90 and above"] += 1
        elif percent >= 80:
            bands["80s"] += 1
        elif percent >= 70:
            bands["70s"] += 1
        else:
            bands["Below 70"] += 1
        detail.append([student, score, possible, percent])
    for label, count in bands.items():
        summary.append([label, count])
    if not patients:
        summary.append(["No assigned copies of this case", 0])
    return _sheet_bytes(book)


def _score(payload: dict | None) -> tuple[float | None, float]:
    if not payload:
        return None, 0
    criteria = payload.get("criteria") or []
    total = 0.0
    possible = 0.0
    any_score = False
    for item in criteria:
        points = item.get("max_points")
        score = item.get("score")
        if points is not None:
            possible += float(points)
        if score is not None and score != "":
            any_score = True
            total += float(score)
    if not any_score:
        return None, possible
    return total, possible


