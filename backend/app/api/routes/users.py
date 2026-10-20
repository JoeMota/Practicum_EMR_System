import uuid

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUser, DbSession
from app.models.user import User
from app.schemas.users import UserActiveOut, UserActivePatch
from app.services.access import memberships_for, require, require_held_role
from app.services.audit import log_event

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/{user_id}/active", response_model=UserActiveOut)
async def set_user_active(
    user_id: uuid.UUID, body: UserActivePatch, db: DbSession, user: CurrentUser, request: Request
):
    rows = await memberships_for(db, user.id)
    require_held_role(user, "admin", rows)
    require("admin", "user:manage_access", "Your role can't manage user access.")
    if user_id == user.id and not body.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "You can't deactivate your own account.")
    target = await db.get(User, user_id)
    if target is None or target.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    target.is_active = body.is_active
    await log_event(
        db,
        action="user.activate" if body.is_active else "user.deactivate",
        entity_type="user",
        entity_id=str(target.id),
        actor_user_id=user.id,
        ip_address=request.client.host if request.client else None,
        detail=f"is_active={body.is_active}",
    )
    await db.commit()
    return {"id": str(target.id), "is_active": target.is_active}