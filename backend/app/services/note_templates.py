"""Built-in note templates stay in code. Saved templates are shared or for one course."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinical import SavedNoteTemplate
from app.services.templates import section_ids


def _saved_id(template_id: str) -> uuid.UUID | None:
    if template_id in _builtin_ids():
        return None
    try:
        return uuid.UUID(template_id)
    except ValueError:
        return None


def _builtin_ids() -> set[str]:
    from app.services.templates import SECTIONS

    return set(SECTIONS)


async def load_saved(db: AsyncSession, template_id: str) -> SavedNoteTemplate | None:
    saved_id = _saved_id(template_id)
    if saved_id is None:
        return None
    return await db.get(SavedNoteTemplate, saved_id)


async def assert_usable(db: AsyncSession, template_id: str, course_id: uuid.UUID) -> None:
    if template_id in _builtin_ids():
        return
    saved = await load_saved(db, template_id)
    if saved is None or (saved.course_id is not None and saved.course_id != course_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown note template.")


async def template_sensitivity(db: AsyncSession, template_id: str) -> str:
    saved = await load_saved(db, template_id)
    if saved is None:
        return "standard"
    if saved.sensitivity in {"psychiatry", "protected"}:
        return saved.sensitivity
    if saved.sensitive:
        return "protected"
    return "standard"


async def is_sensitive(db: AsyncSession, template_id: str) -> bool:
    return await template_sensitivity(db, template_id) != "standard"


async def allowed_section_ids(db: AsyncSession, template_id: str) -> set[str]:
    known = section_ids(template_id)
    if known:
        return known
    saved = await load_saved(db, template_id)
    if saved is None:
        return set()
    return {str(section.get("id")) for section in saved.sections or [] if section.get("id")}


async def templates_for_course(db: AsyncSession, course_id: uuid.UUID | None, *, shared_only: bool) -> list[SavedNoteTemplate]:
    if shared_only:
        query = select(SavedNoteTemplate).where(SavedNoteTemplate.course_id.is_(None))
    else:
        query = select(SavedNoteTemplate).where(
            or_(SavedNoteTemplate.course_id.is_(None), SavedNoteTemplate.course_id == course_id)
        )
    return list((await db.scalars(query.order_by(SavedNoteTemplate.name))).all())
