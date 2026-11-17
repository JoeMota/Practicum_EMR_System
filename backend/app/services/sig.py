"""Build a short pharmacy-style SIG string from dose, route, and frequency."""

from __future__ import annotations

import re

_ROUTE = {
    "po": "PO",
    "oral": "PO",
    "by mouth": "PO",
    "iv": "IV",
    "im": "IM",
    "sc": "SC",
    "sq": "SC",
    "subcut": "SC",
    "subcutaneous": "SC",
    "topical": "TOP",
    "inh": "INH",
    "inhaled": "INH",
    "sl": "SL",
    "pr": "PR",
    "ou": "OU",
    "os": "OS",
    "od": "OD",
}

_FREQUENCY = (
    (re.compile(r"\b(twice daily|twice a day|bid|b\.i\.d\.?)\b", re.I), "BID"),
    (re.compile(r"\b(three times daily|3 times daily|tid|t\.i\.d\.?)\b", re.I), "TID"),
    (re.compile(r"\b(four times daily|4 times daily|qid|q\.i\.d\.?)\b", re.I), "QID"),
    (re.compile(r"\b(once daily|once a day|(?<!\w)daily(?!\w)|q\.?\s*d\.?|(?<!\w)qd(?!\w))\b", re.I), "QD"),
    (re.compile(r"\b(at bedtime|every night|qhs|q\.?h\.?s\.?)\b", re.I), "QHS"),
    (re.compile(r"\b(every morning|qam|q\.?a\.?m\.?)\b", re.I), "QAM"),
    (re.compile(r"\b(every evening|qpm|q\.?p\.?m\.?)\b", re.I), "QPM"),
    (re.compile(r"\b(as needed|prn|p\.r\.n\.?)\b", re.I), "PRN"),
)


def _route(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        return ""
    return _ROUTE.get(cleaned.lower(), cleaned.upper() if len(cleaned) <= 4 else cleaned)


def _frequency(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        return ""
    parts: list[str] = []
    every = re.search(r"(?:every\s*(\d+)\s*hours?|q(\d+)h)", cleaned, re.I)
    if every:
        hours = every.group(1) or every.group(2)
        parts.append(f"Q{hours}H")
    for pattern, label in _FREQUENCY:
        if label == "PRN" and pattern.search(cleaned):
            parts.append("PRN")
            break
        if not parts and pattern.search(cleaned):
            return label
    if parts:
        return " ".join(parts)
    return cleaned


def medication_sig(dose: str | None, route: str | None, frequency: str | None) -> str:
    parts = [part for part in ((dose or "").strip(), _route(route or ""), _frequency(frequency or "")) if part]
    return " ".join(parts)
