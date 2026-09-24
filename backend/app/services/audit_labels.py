"""Human-readable labels for the activity log (FR-05)."""
from __future__ import annotations

from typing import Any

ACTION_LABELS: dict[str, str] = {
    "auth.sign_in": "Signed in",
    "auth.login": "Signed in",
    "auth.login_failed": "Sign-in failed",
    "auth.sso_sign_in": "Signed in with UTEP",
    "auth.sso_failed": "UTEP sign-in failed",
    "auth.sso_unknown_user": "UTEP sign-in — not on roster",
    "auth.duo_sign_in": "Signed in with Duo",
    "auth.duo_failed": "Duo verification failed",
    "auth.password_changed": "Changed password",
    "chart.view": "Opened patient chart",
    "patient.update_status": "Updated patient status",
    "patient.reset_practice": "Reset practice patient",
    "note.view": "Opened clinical note",
    "note.create": "Started a clinical note",
    "note.save_draft": "Saved note draft",
    "note.sign": "Signed note",
    "note.sign_submit": "Submitted note for review",
    "note.cosign": "Co-signed note",
    "note.return": "Returned note for revision",
    "note.addendum": "Added note addendum",
    "roster.import": "Imported roster spreadsheet",
    "roster.add_member": "Added person to course",
    "roster.remove": "Removed person from course",
    "referral.create": "Created referral",
}

ENTITY_LABELS: dict[str, str] = {
    "patient": "Patient",
    "note": "Note",
    "course": "Course",
    "user": "User",
    "referral": "Referral",
}


def action_label(action: str) -> str:
    if action in ACTION_LABELS:
        return ACTION_LABELS[action]
    # Fallback: "note.cosign" → "Note cosign"
    parts = action.replace("_", " ").split(".")
    return " · ".join(p.capitalize() for p in parts if p)


def format_detail(action: str, details: dict[str, Any] | None) -> str | None:
    if not details:
        return None
    d = {k: v for k, v in details.items() if k != "result" and v is not None}
    if not d:
        return None
    if isinstance(d.get("detail"), str) and d["detail"].strip():
        return str(d["detail"]).strip()

    if action == "roster.import":
        added = d.get("added", 0)
        already = d.get("alreadyEnrolled", 0)
        bits = [f"{added} added"]
        if already:
            bits.append(f"{already} already enrolled")
        return "; ".join(bits)

    if action == "roster.add_member":
        role = d.get("appRole") or "member"
        email = d.get("email")
        bits = [f"as {role}"]
        if email:
            bits.append(str(email))
        if d.get("created"):
            bits.append("new account")
        if d.get("alreadyEnrolled"):
            bits.append("already enrolled")
        return " · ".join(bits)

    if action in ("auth.sign_in", "auth.sso_sign_in", "auth.duo_sign_in"):
        channel = d.get("channel")
        method = d.get("method")
        if channel:
            return f"via {channel}"
        if method:
            return f"via {method}"
        return None

    if action in ("auth.login_failed", "auth.sso_unknown_user", "auth.sso_failed", "auth.duo_failed"):
        email = d.get("email")
        err = d.get("error")
        if email:
            return str(email)
        if err:
            return str(err)[:160]
        return None

    if action == "patient.reset_practice":
        n = d.get("archivedNotes")
        if n is not None:
            return f"{n} notes archived"
        return None

    if action == "referral.create":
        to_disc = d.get("toDiscipline") or d.get("to")
        if to_disc:
            return f"to {to_disc}"
        return None

    # Keep short key=value leftovers readable, skip noisy blobs
    parts: list[str] = []
    for key, val in d.items():
        if key in ("error",) and isinstance(val, str):
            parts.append(val[:120])
            continue
        if isinstance(val, (dict, list)):
            continue
        if key in ("email", "channel", "method", "appRole"):
            parts.append(f"{key}: {val}")
    return " · ".join(parts) if parts else None
