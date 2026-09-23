"""Microsoft Entra ID (Azure AD) OIDC helpers for UTEP campus login.

UTEP accounts authenticate at Entra; campus Duo MFA is enforced by UTEP's
Conditional Access / Duo integration on the IdP — this app does not embed Duo
when SSO is used. After a successful Entra login we issue our own short-lived JWT.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWKClient

from app.core.config import settings

ALLOWED_EMAIL_SUFFIXES = ("@utep.edu", "@miners.utep.edu")


@dataclass(frozen=True)
class EntraIdentity:
    email: str
    oid: str | None
    given_name: str | None
    family_name: str | None
    display_name: str | None


def entra_configured() -> bool:
    return bool(
        settings.ENTRA_TENANT_ID.strip()
        and settings.ENTRA_CLIENT_ID.strip()
        and settings.ENTRA_CLIENT_SECRET.strip()
    )


def _authority() -> str:
    tenant = settings.ENTRA_TENANT_ID.strip()
    return f"https://login.microsoftonline.com/{tenant}"


def authorize_url(*, state: str, nonce: str) -> str:
    params = {
        "client_id": settings.ENTRA_CLIENT_ID.strip(),
        "response_type": "code",
        "redirect_uri": settings.ENTRA_REDIRECT_URI.strip(),
        "response_mode": "query",
        "scope": "openid profile email offline_access",
        "state": state,
        "nonce": nonce,
        "prompt": "select_account",
    }
    # Prefer UTEP-branded login when domain hint is set.
    if settings.ENTRA_DOMAIN_HINT.strip():
        params["domain_hint"] = settings.ENTRA_DOMAIN_HINT.strip()
    if settings.ENTRA_LOGIN_HINT_SUFFIX.strip():
        params["login_hint"] = settings.ENTRA_LOGIN_HINT_SUFFIX.strip()
    return f"{_authority()}/oauth2/v2.0/authorize?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    data = {
        "client_id": settings.ENTRA_CLIENT_ID.strip(),
        "client_secret": settings.ENTRA_CLIENT_SECRET.strip(),
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.ENTRA_REDIRECT_URI.strip(),
        "scope": "openid profile email offline_access",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(f"{_authority()}/oauth2/v2.0/token", data=data)
        resp.raise_for_status()
        return resp.json()


def _jwks_client() -> PyJWKClient:
    return PyJWKClient(f"{_authority()}/discovery/v2.0/keys", cache_keys=True)


def decode_id_token(id_token: str, *, expected_nonce: str) -> dict:
    signing_key = _jwks_client().get_signing_key_from_jwt(id_token)
    claims = jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.ENTRA_CLIENT_ID.strip(),
        issuer=f"{_authority()}/v2.0",
        options={"require": ["exp", "iat", "aud", "iss"]},
    )
    if claims.get("nonce") != expected_nonce:
        raise ValueError("OIDC nonce mismatch")
    return claims


def identity_from_claims(claims: dict) -> EntraIdentity:
    email = (
        (claims.get("email") or claims.get("preferred_username") or claims.get("upn") or "")
        .strip()
        .lower()
    )
    if not email or not any(email.endswith(sfx) for sfx in ALLOWED_EMAIL_SUFFIXES):
        raise ValueError("Sign-in must use a UTEP email (@utep.edu or @miners.utep.edu).")
    return EntraIdentity(
        email=email,
        oid=claims.get("oid"),
        given_name=claims.get("given_name"),
        family_name=claims.get("family_name"),
        display_name=claims.get("name"),
    )
