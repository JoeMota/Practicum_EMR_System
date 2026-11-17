"""Course-level dose policy. An empty mode uses the profile default."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinical import Course

PROFILE_DEFAULTS = {
    "intro_pharmacy": "acknowledge",
    "practicum": "advisory",
    "clinical_other": "advisory",
}


async def guardrail_mode(db: AsyncSession, course_id: uuid.UUID) -> str:
    course = await db.get(Course, course_id)
    if course is None:
        return "advisory"
    if course.guardrail_mode:
        return course.guardrail_mode
    return PROFILE_DEFAULTS.get(course.guardrail_profile or "practicum", "advisory")
