"""Section suggestions. The route refuses protected notes before this runs."""

import httpx
from fastapi import HTTPException, status

from app.core.config import settings


async def suggest_section(section_id: str, context: str) -> str:
    url = (settings.AI_API_URL or "").strip()
    if not url:
        raise HTTPException(status.HTTP_409_CONFLICT, "Assist is off.")
    headers = {}
    if (settings.AI_API_KEY or "").strip():
        headers["Authorization"] = f"Bearer {settings.AI_API_KEY}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                url,
                json={"model": settings.AI_MODEL, "section": section_id, "context": context[:6000]},
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Assist is unavailable right now.") from exc
    text = payload.get("suggestion") if isinstance(payload, dict) else None
    if not isinstance(text, str) or not text.strip():
        text = payload.get("text") if isinstance(payload, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Assist did not return a suggestion.")
    return text.strip()[:4000]
