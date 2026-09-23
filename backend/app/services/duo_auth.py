"""Duo Universal Prompt (Web SDK v4) for local-password MFA.

When users sign in with UTEP Entra SSO, Duo is already enforced by campus IdP —
this module is only used for the optional local/demo password path.
"""
from __future__ import annotations

from duo_universal import Client

from app.core.config import settings


def duo_configured() -> bool:
    return bool(
        settings.DUO_CLIENT_ID.strip()
        and settings.DUO_CLIENT_SECRET.strip()
        and settings.DUO_API_HOSTNAME.strip()
    )


def _client() -> Client:
    return Client(
        client_id=settings.DUO_CLIENT_ID.strip(),
        client_secret=settings.DUO_CLIENT_SECRET.strip(),
        host=settings.DUO_API_HOSTNAME.strip(),
        redirect_uri=settings.DUO_REDIRECT_URI.strip(),
    )


def create_auth_url(*, username: str, state: str) -> str:
    client = _client()
    try:
        client.health_check()
    except Exception as exc:  # pragma: no cover - network / misconfig
        raise RuntimeError(f"Duo health check failed: {exc}") from exc
    return client.create_auth_url(username, state)


def exchange_duo_code(*, duo_code: str, username: str) -> dict:
    client = _client()
    return client.exchange_authorization_code_for_2fa_result(duo_code, username)
