"""Turn an uploaded PDF or Word rubric into the grading form. Unreadable files are rejected."""

import io
import re
import uuid

from fastapi import HTTPException, status

_POINTS = re.compile(r"\((\d+)\s*(?:points?|pts?)\)", re.I)
_NUMBERED = re.compile(r"^(?:\d+[\).\]]\s+|[-*]\s+)(?P<label>.+)$")


def guide_from_upload(filename: str, payload: bytes) -> dict:
    lower = filename.lower()
    if lower.endswith(".docx"):
        lines = _docx_lines(payload)
    elif lower.endswith(".pdf"):
        lines = _pdf_lines(payload)
    else:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Upload a PDF or Word (.docx) rubric.")
    criteria = _criteria(lines)
    if not criteria:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "No rubric sections were found. Use a heading or a numbered line for each criterion, with the description on the following line.",
        )
    return {"file_name": filename, "criteria": criteria}


def _docx_lines(payload: bytes) -> list[tuple[str, bool]]:
    try:
        from docx import Document
    except ImportError as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Word support is not installed.") from exc
    document = Document(io.BytesIO(payload))
    lines: list[tuple[str, bool]] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        style = (paragraph.style.name or "") if paragraph.style is not None else ""
        lines.append((text, style.lower().startswith("heading")))
    if not lines:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "That Word file has no text.")
    return lines


def _pdf_lines(payload: bytes) -> list[tuple[str, bool]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "PDF support is not installed.") from exc
    reader = PdfReader(io.BytesIO(payload))
    lines: list[tuple[str, bool]] = []
    for page in reader.pages:
        for raw in (page.extract_text() or "").splitlines():
            text = raw.strip()
            if text:
                lines.append((text, False))
    if not lines:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "No text could be read from that PDF.")
    return lines


def _criteria(lines: list[tuple[str, bool]]) -> list[dict]:
    found: list[dict] = []
    index = 0
    while index < len(lines):
        text, heading = lines[index]
        points = _points(text)
        label = _POINTS.sub("", text).strip(" :-—–")
        numbered = _NUMBERED.match(label)
        if numbered:
            label = numbered.group("label").strip()
        detail = ""
        if index + 1 < len(lines) and not lines[index + 1][1] and not _NUMBERED.match(lines[index + 1][0]):
            nxt = lines[index + 1][0]
            if len(nxt) > len(label) and (heading or numbered or len(label) <= 80):
                detail = nxt
        if (heading or numbered) and 2 <= len(label) <= 120:
            if detail:
                index += 1
            found.append(_item(label, detail, points))
        index += 1
    return found


def _points(text: str) -> int | None:
    match = _POINTS.search(text)
    return int(match.group(1)) if match else None


def _item(label: str, detail: str, points: int | None) -> dict:
    return {
        "id": uuid.uuid4().hex[:8],
        "label": label,
        "detail": detail,
        "max_points": points,
    }
