import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from app.api.deps import CurrentUser, DbSession
from app.models.audit import AuditEvent
from app.models.user import User
from app.schemas.clinical import AuditOut
from app.services.access import full_name, memberships_for, require, require_course, require_held_role

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditOut], response_model_exclude_none=True)
async def list_audit(
    db: DbSession,
    user: CurrentUser,
    role: Annotated[str, Query()],
    course_id: Annotated[uuid.UUID | None, Query()] = None,
):
    rows = await memberships_for(db, user.id)
    student_self = role == "student"
    if student_self:
        if course_id is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose a course to view your activity.")
        require_course(role, course_id, user, rows)
    else:
        require(role, "audit:view", "Your role can't view the audit log.")
        if course_id is None:
            if role != "admin":
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose a course to view its activity.")
            require_held_role(user, role, rows)
        else:
            require_course(role, course_id, user, rows)
    statement = select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(300)
    if course_id is not None:
        statement = statement.where(AuditEvent.course_id == course_id)
    if student_self:
        statement = statement.where(AuditEvent.actor_user_id == user.id)
    events = (await db.scalars(statement)).all()
    payload = []
    for event in events:
        actor = await db.get(User, event.actor_user_id) if event.actor_user_id else None
        entity = event.entity_type if not event.entity_id else f"{event.entity_type}/{event.entity_id}"
        detail = (event.details or {}).get("detail")
        payload.append(
            {
                "id": str(event.id),
                "timestamp": event.occurred_at,
                "actor_id": str(event.actor_user_id) if event.actor_user_id else "",
                "actor_name": full_name(actor) if actor else "Unknown",
                "action": event.action,
                "entity": entity,
                "result": event.result,
                "detail": detail,
            }
        )
    return payload
