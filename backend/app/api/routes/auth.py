import secrets
import uuid
from datetime import datetime, timezone
from typing import Annotated
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from app.api.deps import DbSession, get_current_user_allow_password_change
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, Token
from app.schemas.clinical import (
    AuthProvidersOut,
    AuthTokenResponse,
    ChallengeStartRequest,
    ChallengeStartResponse,
    SendCodeRequest,
    SessionUserOut,
    VerifyCodeRequest,
)
from app.schemas.user import UserOut
from app.services import challenges as challenge_store
from app.services import duo_auth
from app.services import entra
from app.services import sso_state
from app.services.access import list_enrollments
from app.services.audit import log_event
from app.services.auth import authenticate_user, get_user_by_email, get_user_by_id, permission_codes
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


def _frontend_redirect(path: str, **params: str) -> RedirectResponse:
    base = settings.FRONTEND_URL.rstrip("/")
    clean = path if path.startswith("/") else f"/{path}"
    query = urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{base}{clean}"
    if query:
        url = f"{url}?{query}"
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


async def _issue_session(
    *,
    db: DbSession,
    request: Request,
    user: User,
    audit_action: str,
    details: dict | None = None,
) -> AuthTokenResponse:
    user.last_login_at = datetime.now(timezone.utc)
    enrollments = await list_enrollments(db, user.id)
    session_user = session_user_from(user, enrollments)
    await log_event(
        db,
        action=audit_action,
        entity_type="user",
        actor_user_id=user.id,
        entity_id=str(user.id),
        ip_address=_client_ip(request),
        details=details or {},
    )
    await db.commit()
    return AuthTokenResponse(
        access_token=create_access_token(str(user.id)),
        must_change_password=user.must_change_password,
        user=session_user,
    )


@router.get("/providers", response_model=AuthProvidersOut)
async def auth_providers():
    """Login UI capabilities — Entra SSO, Duo MFA, and/or educational local MFA."""
    utep_sso = entra.entra_configured()
    require = bool(settings.AUTH_REQUIRE_UTEP_SSO and utep_sso)
    local = bool(settings.AUTH_ALLOW_LOCAL_LOGIN and not require)
    return AuthProvidersOut(
        utepSso=utep_sso,
        duo=duo_auth.duo_configured(),
        localMfa=local,
        requireUtepSso=require,
    )


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
):
    """Password → JWT (Swagger / scripts). Browser UI uses MFA or UTEP SSO."""
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
    if settings.AUTH_REQUIRE_UTEP_SSO and entra.entra_configured():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sign in with your UTEP account (campus login + Duo).",
        )
    if not settings.AUTH_ALLOW_LOCAL_LOGIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local password login is disabled. Use Sign in with UTEP.",
        )

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

    # Prefer Duo Universal Prompt when configured (real MFA for local password path).
    if duo_auth.duo_configured():
        duo_state = secrets.token_urlsafe(24)
        pending_id = sso_state.create_duo_pending(str(user.id), duo_state)
        try:
            url = duo_auth.create_auth_url(username=user.email, state=pending_id)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Duo is unavailable right now. Try again or contact your instructor. ({exc})",
            ) from exc
        return ChallengeStartResponse(duoAuthUrl=url)

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

    user = await get_user_by_id(db, consumed.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found.")

    return await _issue_session(
        db=db,
        request=request,
        user=user,
        audit_action="auth.sign_in",
        details={"channel": consumed.channel or "sms", "method": "local_mfa"},
    )


@router.get("/sso/login")
async def sso_login(return_path: str = Query("/auth/callback", max_length=200)):
    """Start UTEP campus login (Microsoft Entra). Duo runs as part of UTEP's IdP."""
    if not entra.entra_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="UTEP SSO is not configured. Set ENTRA_TENANT_ID, ENTRA_CLIENT_ID, and ENTRA_CLIENT_SECRET.",
        )
    path = return_path if return_path.startswith("/") else "/auth/callback"
    state, nonce = sso_state.create_sso_state(path)
    return RedirectResponse(url=entra.authorize_url(state=state, nonce=nonce), status_code=status.HTTP_302_FOUND)


@router.get("/sso/callback")
async def sso_callback(
    request: Request,
    db: DbSession,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    if error:
        msg = error_description or error
        return _frontend_redirect("/?sso_error=" + quote(msg))

    if not code or not state:
        return _frontend_redirect("/?sso_error=" + quote("Missing SSO response from UTEP login."))

    pending = sso_state.consume_sso_state(state)
    if pending is None:
        return _frontend_redirect("/?sso_error=" + quote("Your UTEP sign-in expired. Start again."))

    try:
        tokens = await entra.exchange_code(code)
        claims = entra.decode_id_token(tokens["id_token"], expected_nonce=pending.nonce)
        identity = entra.identity_from_claims(claims)
    except Exception as exc:
        await log_event(
            db,
            action="auth.sso_failed",
            entity_type="user",
            ip_address=_client_ip(request),
            details={"error": str(exc)[:300]},
        )
        await db.commit()
        return _frontend_redirect("/?sso_error=" + quote("UTEP login could not be verified. Try again."))

    user = await get_user_by_email(db, identity.email)
    if user is None:
        await log_event(
            db,
            action="auth.sso_unknown_user",
            entity_type="user",
            ip_address=_client_ip(request),
            details={"email": identity.email},
        )
        await db.commit()
        return _frontend_redirect(
            "/?sso_error="
            + quote(
                "You're signed in to UTEP, but you're not on this EMR roster yet. Ask your instructor to import your account."
            )
        )

    if identity.oid and user.entra_oid != identity.oid:
        user.entra_oid = identity.oid
    # Campus SSO replaces local temp-password enforcement.
    user.must_change_password = False

    session = await _issue_session(
        db=db,
        request=request,
        user=user,
        audit_action="auth.sso_sign_in",
        details={"method": "entra", "email": identity.email},
    )
    return _frontend_redirect(
        pending.return_path,
        access_token=session.access_token,
        must_change_password="0",
    )


@router.get("/duo/callback")
async def duo_callback(
    request: Request,
    db: DbSession,
    duo_code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    if error:
        return _frontend_redirect("/?sso_error=" + quote(f"Duo verification failed: {error}"))
    if not duo_code or not state:
        return _frontend_redirect("/?sso_error=" + quote("Missing Duo response."))

    pending = sso_state.consume_duo_pending(state)
    if pending is None:
        return _frontend_redirect("/?sso_error=" + quote("Your Duo sign-in expired. Start again."))

    user = await get_user_by_id(db, uuid.UUID(pending.user_id))
    if user is None:
        return _frontend_redirect("/?sso_error=" + quote("Account not found after Duo."))

    try:
        duo_auth.exchange_duo_code(duo_code=duo_code, username=user.email)
    except Exception as exc:
        await log_event(
            db,
            action="auth.duo_failed",
            entity_type="user",
            actor_user_id=user.id,
            ip_address=_client_ip(request),
            details={"error": str(exc)[:300]},
        )
        await db.commit()
        return _frontend_redirect("/?sso_error=" + quote("Duo could not verify this sign-in."))

    session = await _issue_session(
        db=db,
        request=request,
        user=user,
        audit_action="auth.duo_sign_in",
        details={"method": "duo", "email": user.email},
    )
    return _frontend_redirect(
        pending.return_path,
        access_token=session.access_token,
        must_change_password="1" if session.must_change_password else "0",
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
