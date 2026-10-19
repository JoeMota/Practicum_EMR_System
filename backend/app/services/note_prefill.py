"""Prefill new notes from the chart (DOC-02)."""

from __future__ import annotations

from typing import Any

from app.models.clinical import Patient


def _vitals_block(patient: Patient) -> str:
    vitals = patient.vitals or []
    if not vitals:
        return ""
    return "; ".join(f"{v.label}: {v.value}" for v in vitals)


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
            a.substance + (f" ({a.reaction})" if a.reaction else "") for a in allergies
        )
    else:
        allergy = "NKDA"

    meds = patient.medications or []
    med_text = "; ".join(
        f"{m.name} {m.dose} {m.route} {m.frequency}" for m in meds
    ) or "None listed"

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


# Field ids that exist on each template (keep in sync with frontend noteTemplates.ts).
_TEMPLATE_FIELDS: dict[str, set[str]] = {
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
    """Seed ICD picks from the chart problem list when codes are present."""
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
    fields = _TEMPLATE_FIELDS.get(template_id, set())
    vitals = _vitals_block(patient)
    labs = _labs_block(patient)
    objective = ". ".join(p for p in (vitals, labs) if p)
    draft: dict[str, str] = {}

    def put(field_id: str, value: str) -> None:
        if field_id in fields and value.strip():
            draft[field_id] = value.strip()

    put("reason", patient.chief_complaint or "")
    put("cc", patient.chief_complaint or "")
    put("hpi", patient.hpi or "")
    put("subjective", patient.chief_complaint or "")
    put("objective", objective)
    # Real chart vitals/labs only — no instructional stub that falsely satisfies required exam.
    put("exam", objective)
    put("history", _history_block(patient))
    put("measures", objective or vitals)
    return draft
