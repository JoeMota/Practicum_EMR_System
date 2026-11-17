from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, DbSession, get_current_user_allow_password_change
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User

from app.schemas.auth import ActingRoleRequest, ChangePasswordRequest, RefreshRequest, Token
from app.schemas.clinical import PublicUser
from app.services.access import CLINICAL_ROLES, holds_role, memberships_for
from app.services.audit import log_event
from app.services.auth import authenticate_user, get_user_by_email, get_user_by_id, is_usable
from app.services.serialize import user_out
from app.services.sessions import issue_refresh_token, revoke_refresh_token, rotate_refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])

UserAllowPwChange = Annotated[User, Depends(get_current_user_allow_password_change)]

_IDLE_MS = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
_LOGIN_WINDOW = timedelta(minutes=15)
_LOGIN_MAX = 30
_login_hits: dict[str, deque[datetime]] = defaultdict(deque)
_login_lock = Lock()


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def clear_login_rate_limits() -> None:
    """Test helper: wipe in-memory login throttles between cases."""
    with _login_lock:
        _login_hits.clear()


def _rate_limit_login(ip: str | None) -> None:
    if not ip:
        return
    if settings.ENVIRONMENT in {"test", "testing"}:
        return
    # Pytest uses the emr_test database; don't throttle the suite.
    if "emr_test" in settings.DATABASE_URL:
        return
    now = datetime.now(timezone.utc)
    with _login_lock:
        bucket = _login_hits[ip]
        while bucket and now - bucket[0] > _LOGIN_WINDOW:
            bucket.popleft()
        if len(bucket) >= _LOGIN_MAX:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many sign-in attempts. Try again in a few minutes.")
        bucket.append(now)


async def _default_acting_role(db: DbSession, user: User) -> str | None:
    rows = await memberships_for(db, user.id)
    # Prefer course-bound teaching roles; admin is available via explicit role switch (ADM-05).
    for code in ("instructor", "course_coordinator", "student", "front_desk", "patient", "admin"):
        if holds_role(user, code, rows):
            return code
    if user.roles:
        return user.roles[0].code
    return None


async def _token_for(db: DbSession, user: User) -> Token:
    role = user.acting_role
    refresh = await issue_refresh_token(db, user.id)
    return Token(
        access_token=create_access_token(str(user.id), role=role),
        refresh_token=refresh,
        must_change_password=user.must_change_password,
        user=PublicUser.model_validate(await user_out(db, user)),
    )


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],  # "username" field = email
    db: DbSession,
):
    _rate_limit_login(_client_ip(request))
    email = form.username.strip()
    now = datetime.now(timezone.utc)
    existing = await get_user_by_email(db, email)
    if existing is not None and existing.locked_until is not None and existing.locked_until > now:
        raise HTTPException(status.HTTP_423_LOCKED, "This account is locked. Try again in 15 minutes.")
    user = await authenticate_user(db, email, form.password)
    if user is None:
        if existing is not None and is_usable(existing):
            existing.failed_login_count = (existing.failed_login_count or 0) + 1
            locked = existing.failed_login_count >= 5
            if locked:
                existing.locked_until = now + timedelta(minutes=15)
            await log_event(
                db,
                action="auth.locked" if locked else "auth.login_failed",
                entity_type="user",
                actor_user_id=existing.id,
                entity_id=str(existing.id),
                ip_address=_client_ip(request),
                details={"email": email.lower()},
            )
            await db.commit()
            if locked:
                raise HTTPException(status.HTTP_423_LOCKED, "This account is locked. Try again in 15 minutes.")
        else:
            await log_event(
                db,
                action="auth.login_failed",
                entity_type="user",
                ip_address=_client_ip(request),
                details={"email": email.lower()},
            )
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    user.last_activity_at = now
    user.acting_role = await _default_acting_role(db, user)
    await log_event(
        db,
        action="auth.login",
        entity_type="user",
        actor_user_id=user.id,
        entity_id=str(user.id),
        ip_address=_client_ip(request),
    )
    token = await _token_for(db, user)
    await db.commit()
    return token


@router.post("/refresh", response_model=Token)
async def refresh(body: RefreshRequest, db: DbSession):
    row = await rotate_refresh_token(db, body.refresh_token)
    user = await get_user_by_id(db, row.user_id)
    if user is None or not is_usable(user):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in again.")
    now = datetime.now(timezone.utc)
    # SEC-03: idle refresh cannot extend a silent session forever.
    if user.last_activity_at is not None and now - user.last_activity_at > _IDLE_MS:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Signed out after 15 minutes of inactivity.")
    refresh_token = await issue_refresh_token(db, user.id, family_id=row.family_id)
    await db.commit()
    return Token(
        access_token=create_access_token(str(user.id), role=user.acting_role),
        refresh_token=refresh_token,
        must_change_password=user.must_change_password,
        user=PublicUser.model_validate(await user_out(db, user)),
    )


@router.post("/acting-role", response_model=Token)
async def set_acting_role(body: ActingRoleRequest, db: DbSession, user: CurrentUser, request: Request):
    role = body.role.strip()
    if role not in CLINICAL_ROLES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown role.")
    rows = await memberships_for(db, user.id)
    if not holds_role(user, role, rows):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have that role.")
    user.acting_role = role
    user.last_activity_at = datetime.now(timezone.utc)
    await log_event(
        db,
        action="auth.acting_role",
        entity_type="user",
        actor_user_id=user.id,
        entity_id=str(user.id),
        ip_address=_client_ip(request),
        details={"role": role},
    )
    token = await _token_for(db, user)
    await db.commit()
    return token


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, request: Request, db: DbSession):
    await revoke_refresh_token(db, body.refresh_token)
    await log_event(
        db,
        action="auth.logout",
        entity_type="user",
        ip_address=_client_ip(request),
    )
    await db.commit()


@router.get("/me", response_model=PublicUser, response_model_exclude_none=True)
async def me(user: UserAllowPwChange, db: DbSession):
    return await user_out(db, user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest, request: Request, user: UserAllowPwChange, db: DbSession
):
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if body.current_password == body.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different")

    user.hashed_password = hash_password(body.new_password)
    user.must_change_password = False
    await log_event(
        db,
        action="auth.password_changed",
        entity_type="user",
        actor_user_id=user.id,
        entity_id=str(user.id),
        ip_address=_client_ip(request),
    )
    await db.commit()
