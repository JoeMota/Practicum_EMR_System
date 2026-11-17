"""Import case masters from the required Excel template.

The client's sample spreadsheet was not in the handoff. This template uses the
chart fields they confirmed. A file with different headers is rejected.
"""

import io
import uuid
from datetime import date, datetime

from fastapi import HTTPException, status
from openpyxl import Workbook, load_workbook
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinical import Encounter, Patient
from app.models.user import User
from app.services.audit import log_event
from app.services.cases import _unique_case_mrn
from app.services.charts import _replace_children

HEADERS = (
    "first_name",
    "last_name",
    "dob",
    "sex_at_birth",
    "chief_complaint",
    "hpi",
    "past_medical_history",
    "surgical_history",
    "family_history",
    "social_history",
    "care_setting",
    "encounter_type",
    "allergies",
    "medications",
    "problems",
    "labs",
    "vitals",
    "unit",
    "room",
    "bed",
)


def template_workbook() -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.title = "Cases"
    sheet.append(list(HEADERS))
    sheet.append(
        [
            "Ava",
            "Nguyen",
            "1968-04-12",
            "Female",
            "Sugars running high",
            "Home fasting glucose 160-190.",
            "Type 2 diabetes, hypertension",
            "None",
            "Father with diabetes",
            "Walks twice weekly",
            "Outpatient",
            "Office visit",
            "Sulfa|medication|rash|moderate",
            "Metformin|1000 mg|PO|Twice daily|Type 2 diabetes",
            "E11.9|Type 2 diabetes mellitus without complications",
            "A1c|8.6|%|<7|2026-03-01",
            "BP|142/88",
            "",
            "",
            "",
        ]
    )
    notes = book.create_sheet("Instructions")
    notes.append(["Column", "Required", "Format"])
    notes.append(["first_name, last_name, dob, sex_at_birth", "Yes", "dob is YYYY-MM-DD. sex_at_birth is Male or Female."])
    notes.append(["allergies", "Column required, cells may be blank", "substance|medication|reaction|severity separated by ;"])
    notes.append(["medications", "Column required, cells may be blank", "name|dose|route|frequency|indication separated by ;"])
    notes.append(["problems", "Column required, cells may be blank", "code|description separated by ;"])
    notes.append(["labs", "Column required, cells may be blank", "name|value|unit|reference|YYYY-MM-DD separated by ;"])
    notes.append(["vitals", "Column required, cells may be blank", "label|value separated by ;"])
    notes.append(["unit, room, bed", "Column required, cells may be blank", "Simulated inpatient placement. Leave blank for outpatient."])
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


async def import_cases(db: AsyncSession, *, payload: bytes, actor: User, course_id: uuid.UUID, ip: str | None) -> dict:
    try:
        book = load_workbook(io.BytesIO(payload), data_only=True)
    except Exception as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "That file is not an Excel workbook.") from exc
    sheet = book["Cases"] if "Cases" in book.sheetnames else book.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The workbook is empty.")
    headers = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
    if headers[: len(HEADERS)] != list(HEADERS):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Use the case upload template. The header row does not match.",
        )
    created = 0
    for index, raw in enumerate(rows[1:], start=2):
        if raw is None or all(cell is None or str(cell).strip() == "" for cell in raw):
            continue
        values = {HEADERS[i]: ("" if i >= len(raw) or raw[i] is None else str(raw[i]).strip()) for i in range(len(HEADERS))}
        if not values["first_name"] or not values["last_name"] or not values["dob"] or not values["sex_at_birth"]:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Row {index} needs first name, last name, date of birth, and sex at birth.")
        try:
            born = date.fromisoformat(values["dob"][:10])
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Row {index} has a date of birth that is not YYYY-MM-DD.") from exc
        setting = values["care_setting"] or "Outpatient"
        if setting not in {"Outpatient", "Inpatient", "Emergency", "Discharged"}:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Row {index} has an unknown care setting.")
        patient = Patient(
            mrn=await _unique_case_mrn(db),
            first_name=values["first_name"],
            last_name=values["last_name"],
            dob=born,
            sex_at_birth=values["sex_at_birth"],
            course_id=course_id,
            mode="case",
            case_key=str(uuid.uuid4()),
            created_by=actor,
            chief_complaint=values["chief_complaint"],
            hpi=values["hpi"],
            past_medical_history=values["past_medical_history"],
            surgical_history=values["surgical_history"],
            family_history=values["family_history"],
            social_history=values["social_history"],
            lifecycle="Active",
            encounter_status="Scheduled",
            care_setting=setting,
            unit=values["unit"] or None,
            room=values["room"] or None,
            bed=values["bed"] or None,
            is_training=True,
            encounter=Encounter(type=values["encounter_type"] or "Office visit", date=datetime.now().date()),
        )
        db.add(patient)
        await db.flush()
        await db.refresh(patient, attribute_names=["allergies", "medications", "problems", "labs", "vitals", "encounter"])
        await _replace_children(db, patient, _children(values, index))
        created += 1
    await log_event(
        db,
        action="case.import",
        entity_type="course",
        entity_id=str(course_id),
        actor_user_id=actor.id,
        course_id=course_id,
        ip_address=ip,
        detail=f"{created} cases",
    )
    return {"created": created}


def _split(cell: str) -> list[str]:
    return [part.strip() for part in cell.split(";") if part.strip()]


def _pieces(part: str) -> list[str]:
    return [piece.strip() for piece in part.split("|")]


def _children(values: dict, index: int) -> dict:
    allergies = []
    for part in _split(values["allergies"]):
        bits = _pieces(part)
        if not bits or not bits[0]:
            continue
        category = bits[1] if len(bits) > 1 and bits[1] in {"medication", "food", "environmental"} else "medication"
        allergies.append(
            {
                "substance": bits[0],
                "category": category,
                "reaction": bits[2] if len(bits) > 2 else None,
                "severity": bits[3] if len(bits) > 3 else None,
            }
        )
    medications = []
    for part in _split(values["medications"]):
        bits = _pieces(part)
        if not bits or not bits[0]:
            continue
        medications.append(
            {
                "name": bits[0],
                "dose": bits[1] if len(bits) > 1 else "",
                "route": bits[2] if len(bits) > 2 else "",
                "frequency": bits[3] if len(bits) > 3 else "",
                "indication": bits[4] if len(bits) > 4 else None,
                "adherence": bits[5] if len(bits) > 5 else None,
                "access_cost": bits[6] if len(bits) > 6 else None,
                "status": "active",
            }
        )
    problems = []
    for part in _split(values["problems"]):
        bits = _pieces(part)
        if len(bits) == 1:
            problems.append({"code": None, "description": bits[0]})
        elif bits[1]:
            problems.append({"code": bits[0] or None, "description": bits[1]})
    labs = []
    for part in _split(values["labs"]):
        bits = _pieces(part)
        if not bits or not bits[0]:
            continue
        if len(bits) < 5 or not bits[4]:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Row {index} has a lab without a collected date.")
        labs.append(
            {
                "name": bits[0],
                "value": bits[1] if len(bits) > 1 else "",
                "unit": bits[2] if len(bits) > 2 else "",
                "reference_range": bits[3] if len(bits) > 3 else "",
                "collected_at": bits[4],
            }
        )
    vitals = []
    for part in _split(values["vitals"]):
        bits = _pieces(part)
        if len(bits) >= 2 and bits[0] and bits[1]:
            vitals.append({"label": bits[0], "value": bits[1]})
    return {"allergies": allergies, "medications": medications, "problems": problems, "labs": labs, "vitals": vitals}
