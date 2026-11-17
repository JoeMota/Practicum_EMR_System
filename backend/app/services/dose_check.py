"""Dose parsing and teaching-range flags. A flag is advice until a course mode blocks it."""

import re

REFERENCE_MG = {
    "lisinopril": 10,
    "metformin": 500,
    "atorvastatin": 20,
    "warfarin": 5,
    "sertraline": 50,
    "ibuprofen": 400,
    "acetaminophen": 650,
    "amoxicillin": 500,
    "levothyroxine": 0.1,
    "insulin": 10,
}

_DOSE = re.compile(r"^\s*(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*([A-Za-zμµ]+)?\s*$")
_INLINE = re.compile(r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(mg|mcg|µg|μg|ug|g)\b", re.IGNORECASE)
_MASS = {"mg": 1, "mcg": 0.001, "ug": 0.001, "g": 1000}


def check_dose(dose: str, drug_name: str) -> list[dict[str, str]]:
    text = (dose or "").strip()
    if not text:
        return [{"code": "missing_unit", "message": "Enter a dose with a number and a unit, such as 10 mg."}]
    match = _DOSE.match(text)
    if match is None:
        return [{"code": "missing_unit", "message": "Enter the dose as a number and a unit, such as 10 mg or 10,000 mg."}]
    amount = float(match.group(1).replace(",", ""))
    unit = (match.group(2) or "").lower().replace("µ", "u")
    flags: list[dict[str, str]] = []
    if not unit:
        flags.append({"code": "missing_unit", "message": "Add a unit so the dose can be checked."})
    reference = _reference_mg(drug_name)
    amount_mg = amount * _MASS.get(unit, 1) if unit in _MASS else None
    if reference is not None and unit == "g" and reference >= 1:
        flags.append({"code": "unit_mismatch", "message": "This drug is usually written in mg, not grams."})
    if reference is not None and reference < 1 and unit == "mg" and amount >= 1:
        flags.append({"code": "unit_mismatch", "message": "This drug is usually written in mcg, not mg."})
    extreme = False
    if amount_mg is not None and reference is not None and amount_mg >= reference * 1000:
        extreme = True
    if unit in {"", "mg"} and amount >= 10000:
        extreme = True
    if extreme:
        flags.append({
            "code": "dose_extreme",
            "message": "This dose is far above the usual single dose. Check the number and the unit.",
        })
    return flags


def check_text(text: str, drug_names: list[str]) -> list[dict[str, str]]:
    """Run the dose checker on doses written inside a suggestion or note section."""
    found: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    source = text or ""
    for match in _INLINE.finditer(source):
        dose = f"{match.group(1)} {match.group(2)}"
        window = source[max(0, match.start() - 48): match.end() + 48].casefold()
        matched = [name for name in drug_names if name and name.casefold() in window]
        for drug in matched or [""]:
            for flag in check_dose(dose, drug):
                if flag["code"] == "missing_unit":
                    continue
                key = (flag["code"], flag["message"])
                if key in seen:
                    continue
                seen.add(key)
                found.append(flag)
    return found


def _reference_mg(drug_name: str) -> float | None:
    folded = (drug_name or "").casefold()
    for name, dose in REFERENCE_MG.items():
        if name in folded:
            return dose
    return None
