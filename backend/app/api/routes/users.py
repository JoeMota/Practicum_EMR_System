import re
import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select

from app.api.deps import CurrentUser, DbSession
from app.core.security import hash_password
from app.models.clinical import CourseMembership
from app.models.user import Role, User
from app.schemas.clinical import PortalAccess, PublicUser, TempPassword
from app.schemas.users import AccountUpdate, DeleteAccount, UserActiveOut, UserActivePatch
from app.services.access import memberships_for, require, require_held_role
from app.services.audit import log_event
from app.services.charts import load_patient, utcnow
from app.services.retention import RETENTION, anonymize_user, purge_expired
from app.services.serialize import user_out

router = APIRouter(prefix="/users", tags=["users"])


def _require_account_admin(user: User, rows) -> None:
    require_held_role(user, "admin", rows)
    require("admin", "user:manage_access", "Your role can't manage accounts.")


@router.get("", response_model=list[PublicUser], response_model_exclude_none=True)
async def search_users(
    db: DbSession,
    user: CurrentUser,
    q: Annotated[str, Query()] = "",
):
    rows = await memberships_for(db, user.id)
    _require_account_admin(user, rows)
    term = " ".join(q.split()).lower()
    if len(term) < 2:
        return []
    like = f"%{term}%"
    name = func.lower(User.first_name + " " + User.last_name)
    people = (
        await db.scalars(
            select(User)
            .where(User.deleted_at.is_(None), User.purged_at.is_(None))
            .where(or_(func.lower(User.email).like(like), name.like(like)))
            .order_by(User.last_name, User.first_name)
            .limit(20)
        )
    ).all()
    return [await user_out(db, person) for person in people]


@router.patch("/{user_id}", response_model=PublicUser, response_model_exclude_none=True)
async def update_account(user_id: uuid.UUID, body: AccountUpdate, db: DbSession, user: CurrentUser, request: Request):
    rows = await memberships_for(db, user.id)
    _require_account_admin(user, rows)
    target = await db.get(User, user_id)
    if target is None or target.deleted_at is not None or target.purged_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    email = body.email.strip().lower()
    if not email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email is required.")
    taken = await db.scalar(select(User.id).where(User.email == email, User.id != target.id))
    if taken is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Another account already uses that email.")
    full_name = " ".join(body.full_name.split())
    if not full_name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Name is required.")
    university_id = (body.university_id or "").strip() or None
    is_student = await db.scalar(
        select(CourseMembership.id)
        .join(Role, Role.id == CourseMembership.role_id)
        .where(CourseMembership.user_id == target.id, Role.code == "student")
    )
    if is_student is not None and not re.fullmatch(r"800\d{6}", university_id or ""):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Students need a 9-digit 800 number.")
    first, last = _split(full_name)
    target.first_name = first
    target.last_name = last
    target.email = email
    target.university_id = university_id
    await log_event(
        db,
        action="user.update",
        entity_type="user",
        entity_id=str(target.id),
        actor_user_id=user.id,
        ip_address=request.client.host if request.client else None,
        detail=email,
    )
    await db.commit()
    return await user_out(db, target)


@router.post("/{user_id}/reset-password", response_model=TempPassword)
async def reset_password(user_id: uuid.UUID, db: DbSession, user: CurrentUser, request: Request):
    rows = await memberships_for(db, user.id)
    _require_account_admin(user, rows)
    if user_id == user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "You can't reset your own password here.")
    target = await db.get(User, user_id)
    if target is None or target.deleted_at is not None or target.purged_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    if target.archived_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Reactivate this account before resetting the password.")
    temporary = secrets.token_urlsafe(9)
    target.hashed_password = hash_password(temporary)
    target.must_change_password = True
    await log_event(
        db,
        action="user.password_reset",
        entity_type="user",
        entity_id=str(target.id),
        actor_user_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return TempPassword(email=target.email, password=temporary)


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
    if body.is_active and target.purged_at is None:
        target.archived_at = None
    await db.commit()
    return {"id": str(target.id), "is_active": target.is_active}


@router.post("/{user_id}/archive")
async def archive_user(user_id: uuid.UUID, db: DbSession, user: CurrentUser, request: Request):
    rows = await memberships_for(db, user.id)
    require_held_role(user, "admin", rows)
    require("admin", "user:manage_access", "Your role can't archive accounts.")
    if user_id == user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "You can't archive your own account.")
    target = await db.get(User, user_id)
    if target is None or target.deleted_at is not None or target.purged_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    target.archived_at = utcnow()
    target.is_active = False
    await log_event(
        db,
        action="user.archive",
        entity_type="user",
        entity_id=str(target.id),
        actor_user_id=user.id,
        ip_address=request.client.host if request.client else None,
        detail=f"retained until {(target.archived_at + RETENTION).date().isoformat()}",
    )
    await db.commit()
    return {"id": str(target.id), "archived_at": target.archived_at}


@router.post("/{user_id}/delete")
async def delete_account(user_id: uuid.UUID, body: DeleteAccount, db: DbSession, user: CurrentUser, request: Request):
    rows = await memberships_for(db, user.id)
    _require_account_admin(user, rows)
    if user_id == user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "You can't delete your own account.")
    target = await db.get(User, user_id)
    if target is None or target.deleted_at is not None or target.purged_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    if body.email.strip().lower() != target.email.lower():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Type the account email to confirm.")
    await anonymize_user(db, target)
    await log_event(
        db,
        action="user.delete",
        entity_type="user",
        entity_id=str(target.id),
        actor_user_id=user.id,
        ip_address=request.client.host if request.client else None,
        detail="login anonymized; charts and notes kept",
    )
    await db.commit()
    return {"id": str(target.id)}


@router.post("/purge-expired")
async def purge(db: DbSession, user: CurrentUser, request: Request):
    rows = await memberships_for(db, user.id)
    require_held_role(user, "admin", rows)
    require("admin", "user:manage_access", "Your role can't purge archived accounts.")
    count = await purge_expired(db)
    await log_event(
        db,
        action="user.purge_expired",
        entity_type="user",
        entity_id=str(user.id),
        actor_user_id=user.id,
        ip_address=request.client.host if request.client else None,
        detail=str(count),
    )
    await db.commit()
    return {"purged": count}


@router.post("/portal-access")
async def portal_access(body: PortalAccess, db: DbSession, user: CurrentUser, request: Request):
    rows = await memberships_for(db, user.id)
    require_held_role(user, "admin", rows)
    require("admin", "user:manage_access", "Your role can't create portal access.")
    patient = await load_patient(db, body.patient_id)
    email = body.email.strip().lower()
    person = await db.scalar(select(User).where(User.email == email))
    temporary = None
    if person is None:
        first, last = _split(body.full_name)
        temporary = secrets.token_urlsafe(9)
        person = User(
            email=email,
            first_name=first,
            last_name=last,
            hashed_password=hash_password(temporary),
            must_change_password=True,
            is_active=True,
            portal_patient_id=patient.id,
        )
        db.add(person)
        await db.flush()
    else:
        person.portal_patient_id = patient.id
        person.is_active = True
        person.archived_at = None
    patient_role = await db.scalar(select(Role).where(Role.code == "patient"))
    if patient_role is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Roles are not seeded.")
    await db.refresh(person, attribute_names=["roles"])
    if patient_role not in person.roles:
        person.roles.append(patient_role)
    await log_event(
        db,
        action="user.portal_access",
        entity_type="user",
        entity_id=str(person.id),
        actor_user_id=user.id,
        course_id=patient.course_id,
        ip_address=request.client.host if request.client else None,
        detail=str(patient.id),
    )
    await db.commit()
    return {"id": str(person.id), "email": person.email, "temporary_password": temporary}


def _split(full_name: str) -> tuple[str, str]:
    cleaned = " ".join(full_name.split())
    if " " not in cleaned:
        return cleaned or "Portal", cleaned or "Patient"
    first, last = cleaned.rsplit(" ", 1)
    return first, last