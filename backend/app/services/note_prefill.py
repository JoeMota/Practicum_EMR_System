"""Prefill a new note only with the sections the instructor turned on.

Name, date of birth, and MRN always show in the note header. They are not copied
into the body.
"""

from __future__ import annotations

from typing import Any

from app.clinical_sections import prefill_or_default
from app.models.clinical import Patient


def _vitals_block(patient: Patient) -> str:
    vitals = patient.vitals or []
    if not vitals:
        return ""
    visible = [v for v in vitals if (v.status or "recorded") != "entered_in_error"]
    if not visible:
        return ""
    return "; ".join(f"{v.label}: {v.value}" for v in visible)


def _labs_block(patient: Patient) -> str:
    labs = patient.labs or []
    if not labs:
        return ""
    parts: list[str] = []
    for lab in labs:
        flag = getattr(lab, "flag", None)
        parts.append(f"{lab.name} {lab.value} {lab.unit}" + (f" ({flag})" if flag else ""))
    return "; ".join(parts)


def _history_block(patient: Patient) -> str:
    allergies = patient.allergies or []
    if allergies:
        allergy = "; ".join(
            f"{a.substance} ({a.category})" + (f" {a.reaction}" if a.reaction else "") for a in allergies
        )
    else:
        allergy = "NKDA"
    meds = patient.medications or []
    med_text = "; ".join(f"{m.name} {m.dose} {m.route} {m.frequency}" for m in meds if m.status != "entered_in_error") or "None listed"
    problems = patient.problems or []
    pmh = "; ".join(p.description for p in problems if p.description) or "None listed"
    return "\n".join(
        [
            f"PMH: {pmh}",
            f"PSH: {patient.surgical_history or ''}",
            f"Medications: {med_text}",
            f"Allergies: {allergy}",
            f"FH: {patient.family_history or ''}",
            f"SH: {patient.social_history or ''}",
        ]
    )


_TEMPLATE_FIELDS: dict[str, set[str]] = {
    "pharmacy_soap": {"subjective", "objective", "assessment", "plan"},
    "sbar": {"situation", "background", "assessment", "recommendation"},
    "phone_note": {"account"},
    "telehealth_visit": {"subjective", "objective", "assessment", "plan"},
    "pharmacy_mtm": {
        "reason", "med_experience", "objective", "medrec", "dx", "dtp", "rationale",
        "recommendations", "monitoring", "education", "followup",
    },
    "pt_daily_soap": {
        "visit_number", "subjective", "measures", "interventions", "dx", "progress",
        "plan", "goals",
    },
    "general_soap": {
        "cc", "hpi", "history", "ros", "exam", "dx", "rationale", "plan", "disposition",
    },
}


def diagnoses_from_patient(patient: Patient) -> list[dict[str, str]]:
    if "diagnoses" not in prefill_or_default(patient.prefill_sections):
        return []
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for problem in patient.problems or []:
        code = (problem.code or "").strip()
        if not code or code in seen:
            continue
        seen.add(code)
        out.append({"code": code, "label": problem.description or code})
    return out


def prefill_from_patient(template_id: str, patient: Patient) -> dict[str, Any]:
    enabled = set(prefill_or_default(patient.prefill_sections))
    if not enabled:
        return {}
    fields = _TEMPLATE_FIELDS.get(template_id, set())
    vitals = _vitals_block(patient) if "vitals" in enabled else ""
    labs = _labs_block(patient) if "labs" in enabled else ""
    objective = ". ".join(part for part in (vitals, labs) if part)
    meds = ""
    if "medications" in enabled:
        meds = "; ".join(
            f"{m.name} {m.dose} {m.route} {m.frequency}"
            for m in (patient.medications or [])
            if m.status == "active"
        )
    draft: dict[str, str] = {}

    def put(field_id: str, value: str) -> None:
        if field_id in fields and value.strip():
            draft[field_id] = value.strip()

    if "chief_complaint" in enabled:
        put("reason", patient.chief_complaint or "")
        put("cc", patient.chief_complaint or "")
        put("subjective", patient.chief_complaint or "")
        put("situation", patient.chief_complaint or "")
        put("account", patient.chief_complaint or "")
    if "hpi" in enabled:
        put("hpi", patient.hpi or "")
        put("background", patient.hpi or "")
    if objective:
        put("objective", objective)
        put("exam", objective)
        put("measures", objective or vitals)
    if "history" in enabled:
        put("history", _history_block(patient))
    if meds:
        put("med_experience", meds)
    return draft
