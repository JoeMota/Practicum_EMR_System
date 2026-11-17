import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinical import Course, Patient, PatientIntake
from app.models.user import User
from app.schemas.intake import IntakeData


def defaults_from_patient(patient: Patient) -> IntakeData:
    return IntakeData(
        preferred_name=patient.preferred_name or "",
        pronouns=patient.pronouns or "",
        phone="",
        address="",
        preferred_language="",
        past_medical_history=patient.past_medical_history or "",
        surgical_history=patient.surgical_history or "",
        family_history=patient.family_history or "",
        social_history=patient.social_history or "",
        insurance_payer=patient.insurance_payer or "",
        insurance_member_id=patient.insurance_member_id or "",
        insurance_group_number=patient.insurance_group_number or "",
        emergency_contact_name=patient.emergency_contact_name or "",
        emergency_contact_phone=patient.emergency_contact_phone or "",
        emergency_contact_relationship=patient.emergency_contact_relationship or "",
    )


async def get_intake(db: AsyncSession, patient_id: uuid.UUID) -> PatientIntake | None:
    return await db.scalar(select(PatientIntake).where(PatientIntake.patient_id == patient_id))


async def upsert_intake(
    db: AsyncSession, patient: Patient, data: IntakeData, user: User
) -> list[str]:
    row = await get_intake(db, patient.id)
    previous = IntakeData.model_validate(row.data) if row is not None else defaults_from_patient(patient)
    changed = [
        name for name in IntakeData.model_fields
        if getattr(previous, name) != getattr(data, name)
    ]
    new_data = data.model_dump(mode="json", by_alias=False)
    if row is None:
        row = PatientIntake(
            patient_id=patient.id,
            data=new_data,
            updated_by_user_id=user.id,
        )
        db.add(row)
    else:
        row.data = new_data
        row.updated_by_user_id = user.id
    await db.flush()
    return changed


async def editability(db: AsyncSession, patient: Patient) -> tuple[bool, str | None]:
    if patient.mode == "case":
        return False, "Portal information is not available on case masters."
    course = await db.get(Course, patient.course_id)
    if course is not None and course.status in {"ended", "archived"}:
        return False, "This course has ended and cannot be edited."
    return True, None
