"""Section ids a reviewer may attach a comment to."""

SECTIONS: dict[str, tuple[str, ...]] = {
    "pharmacy_soap": ("S", "O", "A", "P"),
    "sbar": ("S", "B", "A", "R"),
    "phone_note": ("N",),
    "telehealth_visit": ("S", "O", "A", "P"),
    "pharmacy_mtm": ("S", "O", "MR", "A", "P"),
    "pt_daily_soap": ("S", "O", "A", "P"),
    "general_soap": ("S", "O", "A", "P"),
}


def section_ids(template_id: str) -> set[str]:
    return set(SECTIONS.get(template_id, ()))
