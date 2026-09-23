"""Short-lived OAuth/OIDC + Duo state (single-process; swap for Redis in multi-instance)."""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field

TTL_SECONDS = 600


@dataclass
class PendingSso:
    nonce: str
    created_at: float = field(default_factory=time.time)
    return_path: str = "/auth/callback"


@dataclass
class PendingDuo:
    user_id: str
    duo_state: str
    created_at: float = field(default_factory=time.time)
    return_path: str = "/auth/callback"


_sso: dict[str, PendingSso] = {}
_duo: dict[str, PendingDuo] = {}


def _purge(store: dict, now: float) -> None:
    expired = [k for k, v in store.items() if now - v.created_at > TTL_SECONDS]
    for k in expired:
        store.pop(k, None)


def create_sso_state(return_path: str = "/auth/callback") -> tuple[str, str]:
    """Returns (state, nonce)."""
    _purge(_sso, time.time())
    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(16)
    _sso[state] = PendingSso(nonce=nonce, return_path=return_path or "/auth/callback")
    return state, nonce


def consume_sso_state(state: str) -> PendingSso | None:
    _purge(_sso, time.time())
    return _sso.pop(state, None)


def create_duo_pending(user_id: str, duo_state: str, return_path: str = "/auth/callback") -> str:
    """Returns our pending id (also used as Duo state key)."""
    _purge(_duo, time.time())
    pending_id = secrets.token_urlsafe(24)
    _duo[pending_id] = PendingDuo(user_id=user_id, duo_state=duo_state, return_path=return_path)
    return pending_id


def get_duo_pending(pending_id: str) -> PendingDuo | None:
    _purge(_duo, time.time())
    pending = _duo.get(pending_id)
    if pending is None:
        return None
    if time.time() - pending.created_at > TTL_SECONDS:
        _duo.pop(pending_id, None)
        return None
    return pending


def consume_duo_pending(pending_id: str) -> PendingDuo | None:
    _purge(_duo, time.time())
    return _duo.pop(pending_id, None)
