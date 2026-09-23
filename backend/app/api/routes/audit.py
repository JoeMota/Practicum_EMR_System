from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, DbSession
from app.models.audit import AuditEvent
from app.models.user import User
from app.schemas.clinical import AuditEntryOut
from app.services.access import can_read_audit
from sqlalchemy import select

router = APIRouter(prefix="/audit", tags=["audit"])


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
    names: dict = {}
    if actor_ids:
        for u in (await db.scalars(select(User).where(User.id.in_(actor_ids)))).all():
            names[u.id] = u.full_name

    out: list[AuditEntryOut] = []
    for e in events:
        details = e.details or {}
        result = details.get("result", "ok")
        if result not in ("ok", "denied"):
            result = "ok"
        entity = e.entity_type
        if e.entity_id:
            entity = f"{e.entity_type}/{e.entity_id}"
        detail = None
        if isinstance(details, dict):
            detail = details.get("detail") or (
                str({k: v for k, v in details.items() if k != "result"}) if len(details) > 1 else None
            )
        out.append(
            AuditEntryOut(
                id=str(e.id),
                timestamp=e.occurred_at.isoformat(),
                actorId=str(e.actor_user_id) if e.actor_user_id else "",
                actorName=names.get(e.actor_user_id, "System"),
                action=e.action,
                entity=entity,
                result=result,
                detail=detail if isinstance(detail, str) else None,
            )
        )
    return out
