"""Chart sections an instructor can lock, and note fields they can choose to prefill."""

SECTION_IDS = (
    "medications",
    "allergies",
    "vitals",
    "lung_sounds",
    "labs",
    "diagnoses",
    "medical_history",
    "surgical_history",
    "chief_complaint",
)

# Students can edit medications, allergies, vitals, lung sounds, and labs unless the instructor locks them.
# Diagnoses, histories, and the chief complaint stay locked until an instructor opens them.
DEFAULT_SECTION_LOCKS: dict[str, bool] = {
    "medications": False,
    "allergies": False,
    "vitals": False,
    "lung_sounds": False,
    "labs": False,
    "diagnoses": True,
    "medical_history": True,
    "surgical_history": True,
    "chief_complaint": True,
}

LUNG_SOUND_LOCATIONS = ("RUL", "RML", "RLL", "LUL", "LLL")
LUNG_SOUND_FINDINGS = ("clear", "crackles", "wheeze", "diminished", "rhonchi", "other")

PREFILL_OPTIONS = (
    "chief_complaint",
    "hpi",
    "vitals",
    "labs",
    "history",
    "medications",
    "diagnoses",
)

ALLERGY_CATEGORIES = ("medication", "food", "environmental")

# Office and related E/M codes. The full CPT set is copyrighted by the AMA and is not included.
# Amounts are intentionally absent.
DELETED_CPT_CODES = ("99441", "99442", "99443")  # Deleted in 2025; replacements need customer approval.
CPT_CODES: list[dict[str, str]] = [
    {"code": "99211", "label": "Office visit, established patient, level 1"},
    {"code": "99212", "label": "Office visit, established patient, level 2"},
    {"code": "99213", "label": "Office visit, established patient, level 3"},
    {"code": "99214", "label": "Office visit, established patient, level 4"},
    {"code": "99215", "label": "Office visit, established patient, level 5"},
    {"code": "99202", "label": "Office visit, new patient, level 2"},
    {"code": "99203", "label": "Office visit, new patient, level 3"},
    {"code": "99204", "label": "Office visit, new patient, level 4"},
    {"code": "99205", "label": "Office visit, new patient, level 5"},
    {"code": "99221", "label": "Initial hospital care, level 1"},
    {"code": "99222", "label": "Initial hospital care, level 2"},
    {"code": "99223", "label": "Initial hospital care, level 3"},
    {"code": "99231", "label": "Subsequent hospital care, level 1"},
    {"code": "99232", "label": "Subsequent hospital care, level 2"},
    {"code": "99233", "label": "Subsequent hospital care, level 3"},
    {"code": "99238", "label": "Hospital discharge, 30 minutes or less"},
    {"code": "99239", "label": "Hospital discharge, more than 30 minutes"},
]


def locks_or_default(value: dict | None) -> dict[str, bool]:
    merged = dict(DEFAULT_SECTION_LOCKS)
    for key, locked in (value or {}).items():
        if key in merged:
            merged[key] = bool(locked)
    return merged


def prefill_or_default(value: list | None) -> list[str]:
    return [item for item in (value or []) if item in PREFILL_OPTIONS]
