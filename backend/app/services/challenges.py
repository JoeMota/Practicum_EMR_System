"""In-memory MFA challenges (FR-10). Fine for single-process uvicorn; swap for
Redis if you run multiple workers."""
from __future__ import annotations

import secrets
import time
import uuid
from dataclasses import dataclass, field

# Dev/demo OTP — production would send a random code via SMS/email.
DEV_CODE = "123456"
CHALLENGE_TTL_SECONDS = 10 * 60


@dataclass
class Challenge:
    user_id: uuid.UUID
    created_at: float = field(default_factory=time.time)
    channel: str | None = None
    code: str = DEV_CODE


_challenges: dict[str, Challenge] = {}


def create_challenge(user_id: uuid.UUID) -> str:
    challenge_id = f"ch_{secrets.token_hex(8)}"
    _challenges[challenge_id] = Challenge(user_id=user_id)
    return challenge_id


def get_challenge(challenge_id: str) -> Challenge | None:
    ch = _challenges.get(challenge_id)
    if ch is None:
        return None
    if time.time() - ch.created_at > CHALLENGE_TTL_SECONDS:
        _challenges.pop(challenge_id, None)
        return None
    return ch


def set_channel(challenge_id: str, channel: str) -> Challenge | None:
    ch = get_challenge(challenge_id)
    if ch is None:
        return None
    ch.channel = channel
    return ch


def consume_challenge(challenge_id: str, code: str) -> Challenge | None:
    ch = get_challenge(challenge_id)
    if ch is None:
        return None
    if code.strip() != ch.code:
        return None
    _challenges.pop(challenge_id, None)
    return ch
