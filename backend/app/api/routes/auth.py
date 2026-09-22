from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from app.api.deps import DbSession, get_current_user_allow_password_change
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, Token
from app.schemas.clinical import (
    AuthTokenResponse,
    ChallengeStartRequest,
    ChallengeStartResponse,
    SendCodeRequest,
    SessionUserOut,
    VerifyCodeRequest,
)
from app.schemas.user import UserOut
from app.services import challenges as challenge_store
from app.services.access import list_enrollments
from app.services.audit import log_event
from app.services.auth import authenticate_user, permission_codes
from app.services.serializers import session_user_from

router = APIRouter(prefix="/auth", tags=["auth"])

UserAllowPwChange = Annotated[User, Depends(get_current_user_allow_password_change)]

ALLOWED_EMAIL = ("@utep.edu", "@miners.utep.edu")


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _mask_email(email: str) -> str:
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if not local:
        return f"•••@{domain}"
    return f"{local[0]}•••@{domain}"


def _assert_utep_email(email: str) -> None:
    lowered = email.strip().lower()
    if not any(lowered.endswith(sfx) for sfx in ALLOWED_EMAIL):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use your UTEP email address (@utep.edu or @miners.utep.edu).",
        )


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
):
    """Password → JWT (Swagger / scripts). Browser UI uses the MFA challenge flow."""
    user = await authenticate_user(db, form.username, form.password)
    if user is None:
        await log_event(
            db,
            action="auth.login_failed",
            entity_type="user",
            ip_address=_client_ip(request),
            details={"email": form.username.strip().lower()},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.last_login_at = datetime.now(timezone.utc)
    await log_event(
        db,
        action="auth.login",
        entity_type="user",
        actor_user_id=user.id,
        entity_id=str(user.id),
        ip_address=_client_ip(request),
    )
    await db.commit()
    return Token(
        access_token=create_access_token(str(user.id)),
        must_change_password=user.must_change_password,
    )


@router.post("/challenge", response_model=ChallengeStartResponse)
async def start_challenge(body: ChallengeStartRequest, request: Request, db: DbSession):
    _assert_utep_email(body.email)
    user = await authenticate_user(db, body.email, body.password)
    if user is None:
        await log_event(
            db,
            action="auth.login_failed",
            entity_type="user",
            ip_address=_client_ip(request),
            details={"email": body.email.strip().lower()},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That email and password don't match an EMR account. Ask your instructor to confirm you're on the course roster.",
        )
    challenge_id = challenge_store.create_challenge(user.id)
    return ChallengeStartResponse(
        challengeId=challenge_id,
        phoneLast4=user.phone_last4,
        emailMasked=_mask_email(user.email),
    )


@router.post("/send-code", status_code=status.HTTP_204_NO_CONTENT)
async def send_code(body: SendCodeRequest):
    ch = challenge_store.set_channel(body.challengeId, body.channel)
    if ch is None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Your sign-in expired. Start again.")
    # Educational build: code is always DEV_CODE; production would SMS/email it.


@router.post("/verify-code", response_model=AuthTokenResponse)
async def verify_code(body: VerifyCodeRequest, request: Request, db: DbSession):
    ch = challenge_store.get_challenge(body.challengeId)
    if ch is None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Your sign-in expired. Start again.")
    if body.code.strip() != ch.code:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="That code isn't right. Check the latest message and try again.")

    consumed = challenge_store.consume_challenge(body.challengeId, body.code)
    if consumed is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="That code isn't right. Check the latest message and try again.")

    from app.services.auth import get_user_by_id

    user = await get_user_by_id(db, consumed.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found.")

    user.last_login_at = datetime.now(timezone.utc)
    enrollments = await list_enrollments(db, user.id)
    session_user = session_user_from(user, enrollments)

    await log_event(
        db,
        action="auth.sign_in",
        entity_type="user",
        actor_user_id=user.id,
        entity_id=str(user.id),
        ip_address=_client_ip(request),
        details={"channel": consumed.channel or "sms"},
    )
    await db.commit()

    return AuthTokenResponse(
        access_token=create_access_token(str(user.id)),
        must_change_password=user.must_change_password,
        user=session_user,
    )


@router.get("/me", response_model=SessionUserOut)
async def me(user: UserAllowPwChange, db: DbSession):
    enrollments = await list_enrollments(db, user.id)
    return session_user_from(user, enrollments)


@router.get("/me/permissions", response_model=UserOut)
async def me_permissions(user: UserAllowPwChange):
    """Raw RBAC view for debugging / future admin UI."""
    return UserOut(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        discipline=user.discipline.code if user.discipline else None,
        must_change_password=user.must_change_password,
        roles=sorted(role.code for role in user.roles),
        permissions=sorted(permission_codes(user)),
    )


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
