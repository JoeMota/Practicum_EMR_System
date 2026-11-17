"""Encrypt protected note text so a database read does not show it."""

import base64
import hashlib
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

PROTECTED = {"psychiatry", "protected"}


def _key() -> bytes:
    raw = (settings.NOTE_CONTENT_KEY or "").strip() or settings.JWT_SECRET_KEY
    return hashlib.sha256(raw.encode()).digest()


def encrypt_text(plain: str) -> str:
    nonce = os.urandom(12)
    token = nonce + AESGCM(_key()).encrypt(nonce, plain.encode(), None)
    return base64.b64encode(token).decode()


def decrypt_text(token: str) -> str:
    raw = base64.b64decode(token)
    return AESGCM(_key()).decrypt(raw[:12], raw[12:], None).decode()


def encrypt_json(payload: dict) -> str:
    return encrypt_text(json.dumps(payload))


def decrypt_json(token: str) -> dict:
    loaded = json.loads(decrypt_text(token))
    return loaded if isinstance(loaded, dict) else {}


def note_is_protected(note) -> bool:
    kind = getattr(note, "sensitivity", None) or "standard"
    return kind in PROTECTED or bool(getattr(note, "sensitive", False) and kind == "standard")


def seal_note(note) -> None:
    kind = note.sensitivity or "standard"
    if kind not in PROTECTED:
        if note.content_cipher:
            note.content = decrypt_json(note.content_cipher)
        note.content_cipher = None
        note.sensitive = False
        note.sensitivity = "standard"
        return
    note.sensitive = True
    note.sensitivity = kind
    source = note.content or {}
    if source:
        note.content_cipher = encrypt_json(source)
    elif not note.content_cipher:
        note.content_cipher = encrypt_json({})
    note.content = {}


def reveal_content(note) -> dict:
    if note.content_cipher:
        return decrypt_json(note.content_cipher)
    return dict(note.content or {})


def seal_text(note, text: str) -> tuple[str, str | None]:
    if note.sensitivity not in PROTECTED and not note.sensitive:
        return text, None
    return "", encrypt_text(text)


def reveal_text(body: str, cipher: str | None) -> str:
    if cipher:
        return decrypt_text(cipher)
    return body
