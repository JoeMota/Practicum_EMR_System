import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.audit import AuditEvent
from app.models.course import Course
from app.models.note import ClinicalNote
from app.models.patient import Patient
from app.models.user import User
from app.schemas.clinical import AuditEntryOut
from app.services.access import can_read_audit
from app.services.audit_labels import ENTITY_LABELS, action_label, format_detail

router = APIRouter(prefix="/audit", tags=["audit"])


def _short_id(value: str | None) -> str:
    if not value:
        return ""
    text = str(value)
    if len(text) <= 8:
        return text
    return text[:8]


@router.get("", response_model=list[AuditEntryOut])
async def list_audit(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(200, ge=1, le=1000),
):
    if not can_read_audit(user):
        raise HTTPException(status_code=403, detail="Missing permission: audit:read")

    events = (
        await db.scalars(select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(limit))
    ).all()

    actor_ids = {e.actor_user_id for e in events if e.actor_user_id}
    names: dict[uuid.UUID, str] = {}
    if actor_ids:
        for u in (await db.scalars(select(User).where(User.id.in_(actor_ids)))).all():
            names[u.id] = u.full_name

    patient_ids: set[uuid.UUID] = set()
    note_ids: set[uuid.UUID] = set()
    course_ids: set[uuid.UUID] = set()
    user_ids: set[uuid.UUID] = set()
    for e in events:
        if not e.entity_id:
            continue
        try:
            eid = uuid.UUID(str(e.entity_id))
        except ValueError:
            continue
        if e.entity_type == "patient":
            patient_ids.add(eid)
        elif e.entity_type == "note":
            note_ids.add(eid)
        elif e.entity_type == "course":
            course_ids.add(eid)
        elif e.entity_type == "user":
            user_ids.add(eid)

    patients: dict[uuid.UUID, Patient] = {}
    if patient_ids:
        for p in (await db.scalars(select(Patient).where(Patient.id.in_(patient_ids)))).all():
            patients[p.id] = p

    notes: dict[uuid.UUID, ClinicalNote] = {}
    note_patient_ids: set[uuid.UUID] = set()
    if note_ids:
        for n in (await db.scalars(select(ClinicalNote).where(ClinicalNote.id.in_(note_ids)))).all():
            notes[n.id] = n
            note_patient_ids.add(n.patient_id)
        missing = note_patient_ids - set(patients)
        if missing:
            for p in (await db.scalars(select(Patient).where(Patient.id.in_(missing)))).all():
                patients[p.id] = p

    courses: dict[uuid.UUID, Course] = {}
    if course_ids:
        for c in (await db.scalars(select(Course).where(Course.id.in_(course_ids)))).all():
            courses[c.id] = c

    user_labels: dict[uuid.UUID, str] = dict(names)
    if user_ids:
        for u in (await db.scalars(select(User).where(User.id.in_(user_ids)))).all():
            user_labels[u.id] = u.full_name

    out: list[AuditEntryOut] = []
    for e in events:
        details = e.details if isinstance(e.details, dict) else {}
        result = details.get("result", "ok")
        if result not in ("ok", "denied"):
            result = "ok"

        type_label = ENTITY_LABELS.get(e.entity_type, e.entity_type.replace("_", " ").capitalize() or "Record")
        record_label = type_label
        entity_key = e.entity_type
        if e.entity_id:
            entity_key = f"{e.entity_type}/{e.entity_id}"

        try:
            eid = uuid.UUID(str(e.entity_id)) if e.entity_id else None
        except ValueError:
            eid = None

        if eid and e.entity_type == "patient" and eid in patients:
            p = patients[eid]
            record_label = f"Patient · {p.first_name} {p.last_name} ({p.mrn})"
        elif eid and e.entity_type == "note" and eid in notes:
            n = notes[eid]
            p = patients.get(n.patient_id)
            who = n.author_name or "student"
            if p:
                record_label = f"Note · {who} on {p.first_name} {p.last_name}"
            else:
                record_label = f"Note · {who}"
        elif eid and e.entity_type == "course" and eid in courses:
            c = courses[eid]
            record_label = f"Course · {c.code}"
        elif eid and e.entity_type == "user":
            record_label = f"User · {user_labels.get(eid, _short_id(str(eid)))}"
        elif e.entity_id:
            record_label = f"{type_label} · {_short_id(e.entity_id)}"

        out.append(
            AuditEntryOut(
                id=str(e.id),
                timestamp=e.occurred_at.isoformat(),
                actorId=str(e.actor_user_id) if e.actor_user_id else "",
                actorName=names.get(e.actor_user_id, "System") if e.actor_user_id else "System",
                action=e.action,
                actionLabel=action_label(e.action),
                entity=entity_key,
                recordLabel=record_label,
                result=result,
                detail=format_detail(e.action, details),
            )
        )
    return out
