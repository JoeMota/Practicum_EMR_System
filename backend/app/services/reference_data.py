"""External vocabularies. Lexicomp is not called unless a URL is configured."""

import json
from pathlib import Path

import httpx
from fastapi import HTTPException, status

from app.clinical_sections import CPT_CODES
from app.core.config import settings

_ICD_URL = "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search"
_RXNAV_URL = "https://rxnav.nlm.nih.gov/REST/approximateTerm.json"


async def search_icd10(term: str) -> list[dict[str, str]]:
    query = term.strip()
    if len(query) < 2:
        return []
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(_ICD_URL, params={"sf": "code,name", "terms": query, "maxList": 25})
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "ICD-10 search is unavailable right now.") from exc
    codes = payload[1] if isinstance(payload, list) and len(payload) > 3 else []
    names = payload[3] if isinstance(payload, list) and len(payload) > 3 else []
    results = []
    for code, name in zip(codes, names, strict=False):
        label = name[0] if isinstance(name, list) and name else str(name)
        results.append({"code": str(code), "label": label})
    return results


async def search_medications(term: str) -> list[dict[str, str]]:
    query = term.strip()
    if len(query) < 2:
        return []
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(_RXNAV_URL, params={"term": query, "maxEntries": 20})
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Medication search is unavailable. The Lexicomp catalog is not connected.",
        ) from exc
    candidates = payload.get("approximateGroup", {}).get("candidate") or []
    seen: set[str] = set()
    results = []
    for item in candidates:
        name = (item.get("name") or "").strip()
        key = name.lower()
        if not name or key in seen:
            continue
        seen.add(key)
        results.append({"name": name, "rxcui": item.get("rxcui") or ""})
    return results


async def medication_details(rxcui: str) -> dict:
    identifier = rxcui.strip()
    if not identifier.isdigit():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose a medication from the list.")
    url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{identifier}/related.json"
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(url, params={"tty": "IN+BN"})
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Medication details are unavailable right now.") from exc
    generic = ""
    brands: list[str] = []
    for group in payload.get("relatedGroup", {}).get("conceptGroup") or []:
        tty = group.get("tty")
        for concept in group.get("conceptProperties") or []:
            name = (concept.get("name") or "").strip()
            if not name:
                continue
            if tty == "IN" and not generic:
                generic = name
            elif tty == "BN" and name not in brands:
                brands.append(name)
    return {"rxcui": identifier, "genericName": generic, "brandNames": brands[:8]}


def _teaching_text(medications: list[str]) -> str:
    path = Path(__file__).resolve().parents[1] / "data" / "teaching_interactions.json"
    pairs = json.loads(path.read_text())
    folded = [name.casefold() for name in medications if name and name.strip()]
    notes: list[str] = []
    for pair in pairs:
        drugs = [str(item).casefold() for item in pair.get("drugs") or []]
        if drugs and all(any(drug in name for name in folded) for drug in drugs):
            note = str(pair.get("note") or "").strip()
            if note:
                notes.append(note)
    if not notes:
        return "Teaching interaction check. No pairs in the teaching set matched these medications."
    return "Teaching interaction check. " + " ".join(notes)


def search_cpt(term: str) -> list[dict[str, str]]:
    query = term.strip().lower()
    rows = CPT_CODES
    if query:
        rows = [row for row in rows if query in row["code"].lower() or query in row["label"].lower()]
    return rows


def lexicomp_status() -> dict:
    library = (settings.LEXICOMP_URL or "").strip() or None
    api_url = (settings.LEXICOMP_API_URL or "").strip()
    api_key = (settings.LEXICOMP_API_KEY or "").strip()
    configured = bool(api_url and api_key)
    if configured:
        detail = "Interaction results come from Lexicomp."
    else:
        detail = "The interaction check is unavailable."
    return {"configured": configured, "url": library, "detail": detail}


async def lexicomp_interactions(medications: list[str]) -> dict:
    api_url = (settings.LEXICOMP_API_URL or "").strip()
    api_key = (settings.LEXICOMP_API_KEY or "").strip()
    if not api_url or not api_key:
        return {"configured": False, "text": _teaching_text(medications)}
    names = [name.strip() for name in medications if name and name.strip()]
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.post(
                api_url,
                json={"medications": names},
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Lexicomp is unavailable right now.") from exc
    text = payload.get("text") if isinstance(payload, dict) else None
    if text is None and isinstance(payload, dict):
        text = payload.get("interactions")
    if not isinstance(text, str):
        text = None
    return {"configured": True, "text": text}
