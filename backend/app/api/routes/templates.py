import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.models.clinical import SavedNoteTemplate
from app.schemas.clinical import NoteTemplateIn, NoteTemplateOut, TemplateSectionIn
from app.services.access import ensure_course_open, memberships_for, require, require_course, require_held_role
from app.services.note_templates import templates_for_course

router = APIRouter(prefix="/note-templates", tags=["note-templates"])


def _sections(sections: list[TemplateSectionIn]) -> list[dict]:
    seen: set[str] = set()
    dumped = []
    for section in sections:
        if section.id in seen:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Each section needs its own id.")
        seen.add(section.id)
        dumped.append(section.model_dump())
    return dumped


def _out(row: SavedNoteTemplate) -> dict:
    return {
        "id": str(row.id),
        "name": row.name,
        "discipline": row.discipline,
        "scope": "shared" if row.course_id is None else "course",
        "sensitive": row.sensitive,
        "sensitivity": row.sensitivity or ("protected" if row.sensitive else "standard"),
        "sections": row.sections or [],
    }


def _classify(sensitive: bool, sensitivity: str | None) -> tuple[bool, str]:
    kind = sensitivity or ("protected" if sensitive else "standard")
    if kind not in {"standard", "psychiatry", "protected"}:
        kind = "standard"
    return kind != "standard", kind


@router.get("", response_model=list[NoteTemplateOut])
async def list_note_templates(
    db: DbSession,
    user: CurrentUser,
    role: Annotated[str, Query()],
    course_id: Annotated[uuid.UUID | None, Query()] = None,
):
    rows = await memberships_for(db, user.id)
    if course_id is None:
        require_held_role(user, "admin", rows)
        require(role, "course:create", "Your role can't list shared templates.")
        saved = await templates_for_course(db, None, shared_only=True)
    else:
        require_course(role, course_id, user, rows)
        saved = await templates_for_course(db, course_id, shared_only=False)
    return [_out(row) for row in saved]


@router.post("", response_model=NoteTemplateOut)
async def create_note_template(
    body: NoteTemplateIn,
    db: DbSession,
    user: CurrentUser,
    role: Annotated[str, Query()],
):
    rows = await memberships_for(db, user.id)
    if body.course_id is None:
        require_held_role(user, "admin", rows)
        require(role, "course:create", "Your role can't save a shared template.")
    else:
        require_course(role, body.course_id, user, rows)
        if role not in {"instructor", "course_coordinator"}:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role can't save a template for this course.")
        await ensure_course_open(db, body.course_id)
    sensitive, sensitivity = _classify(body.sensitive, body.sensitivity)
    row = SavedNoteTemplate(
        name=body.name.strip(),
        discipline=body.discipline,
        course_id=body.course_id,
        sensitive=sensitive,
        sensitivity=sensitivity,
        sections=_sections(body.sections),
        created_by_id=user.id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _out(row)
