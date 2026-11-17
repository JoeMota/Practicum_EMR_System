"""Ended courses, sensitive templates, photos, and Lexicomp."""

import httpx
import pytest

from app.services.reference_data import lexicomp_interactions
from tests.test_sprint3 import DEMO_CASE
from tests.test_workflows import course_id, login, patient_by_mrn

FIRST_PHOTO = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
SECOND_PHOTO = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="


@pytest.mark.asyncio
async def test_students_cannot_open_an_ended_course(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    admin, _ = await login(client, "gerardo.sillas@utep.edu", role="admin")
    student, _ = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    ended = await client.post(f"/api/v1/courses/{course}/status", headers=admin, json={"status": "ended"})
    assert ended.status_code == 200, ended.text

    blocked = await client.get("/api/v1/patients", headers=student, params={"course_id": course, "role": "student"})
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "This course has ended."

    still_open = await client.get("/api/v1/patients", headers=instructor, params={"course_id": course, "role": "instructor"})
    assert still_open.status_code == 200, still_open.text


@pytest.mark.asyncio
async def test_student_cannot_read_a_sensitive_note(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    student, _ = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    created = await client.post(
        "/api/v1/note-templates",
        headers=instructor,
        params={"role": "instructor"},
        json={
            "name": "Behavioral health check-in",
            "discipline": "pharmacy",
            "courseId": course,
            "sensitive": True,
            "sections": [{"id": "N", "title": "Note", "fields": [{"id": "body", "label": "Private note", "kind": "textarea"}]}],
        },
    )
    assert created.status_code == 200, created.text
    template_id = created.json()["id"]
    chart = await patient_by_mrn(client, student, course, "student", "TR-10021-DR")
    note = await client.post(
        f"/api/v1/patients/{chart['id']}/notes",
        headers=student,
        params={"role": "student"},
        json={"templateId": template_id, "discipline": "pharmacy"},
    )
    assert note.status_code == 200, note.text
    note_id = note.json()["id"]

    listed = await client.get(f"/api/v1/patients/{chart['id']}/notes", headers=student, params={"role": "student"})
    assert listed.status_code == 200, listed.text
    assert note_id not in listed.text
    assert "Private note" not in listed.text

    hidden = await client.get(f"/api/v1/notes/{note_id}", headers=student, params={"role": "student"})
    assert hidden.status_code == 404
    assert note_id not in hidden.text

    opened = await client.get(f"/api/v1/notes/{note_id}", headers=instructor, params={"role": "instructor"})
    assert opened.status_code == 200, opened.text
    audit = await client.get("/api/v1/audit", headers=instructor, params={"course_id": course, "role": "instructor"})
    assert audit.status_code == 200, audit.text
    assert any(row["action"] == "note.view_sensitive" and note_id in row["entity"] for row in audit.json())


@pytest.mark.asyncio
async def test_assigned_chart_keeps_the_photo_from_assignment(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    student, session = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    created = await client.post(
        "/api/v1/cases", headers=instructor, params={"course_id": course, "role": "instructor"}, json=DEMO_CASE,
    )
    assert created.status_code == 200, created.text
    master_id = created.json()["id"]
    saved = await client.put(
        f"/api/v1/patients/{master_id}/photo",
        headers=instructor,
        params={"role": "instructor"},
        json={"contentType": "image/png", "data": FIRST_PHOTO},
    )
    assert saved.status_code == 200, saved.text

    assigned = await client.post(
        "/api/v1/patients",
        headers=instructor,
        params={"course_id": course, "role": "instructor"},
        json={"sourcePatientId": master_id, "ownerId": session["user"]["id"]},
    )
    assert assigned.status_code == 200, assigned.text
    copy_id = assigned.json()["id"]
    assert assigned.json()["hasPhoto"] is True

    first = await client.get(f"/api/v1/patients/{copy_id}/photo", headers=student, params={"role": "student"})
    assert first.status_code == 200, first.text
    assert first.json()["data"] == FIRST_PHOTO

    changed = await client.put(
        f"/api/v1/patients/{master_id}/photo",
        headers=instructor,
        params={"role": "instructor"},
        json={"contentType": "image/png", "data": SECOND_PHOTO},
    )
    assert changed.status_code == 200, changed.text
    again = await client.get(f"/api/v1/patients/{copy_id}/photo", headers=student, params={"role": "student"})
    assert again.status_code == 200, again.text
    assert again.json()["data"] == FIRST_PHOTO


@pytest.mark.asyncio
async def test_lexicomp_does_not_invent_a_result(monkeypatch):
    monkeypatch.setattr("app.services.reference_data.settings.LEXICOMP_API_URL", None)
    monkeypatch.setattr("app.services.reference_data.settings.LEXICOMP_API_KEY", None)
    calls = {"count": 0}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            calls["count"] += 1
            raise AssertionError("unconfigured check must not call Lexicomp")

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    quiet = await lexicomp_interactions(["warfarin", "aspirin"])
    assert quiet["configured"] is False
    assert quiet["text"].startswith("Teaching interaction check.")
    assert calls["count"] == 0

    monkeypatch.setattr("app.services.reference_data.settings.LEXICOMP_API_URL", "https://lexicomp.test/interactions")
    monkeypatch.setattr("app.services.reference_data.settings.LEXICOMP_API_KEY", "test-key")

    class LiveClient(FakeClient):
        async def post(self, url, json, headers):
            calls["count"] += 1
            assert url == "https://lexicomp.test/interactions"
            assert headers["Authorization"] == "Bearer test-key"
            assert json == {"medications": ["warfarin", "aspirin"]}

            class Response:
                def raise_for_status(self):
                    return None

                def json(self):
                    return {"text": "Increased bleeding risk."}

            return Response()

    monkeypatch.setattr(httpx, "AsyncClient", LiveClient)
    found = await lexicomp_interactions(["warfarin", "aspirin"])
    assert found == {"configured": True, "text": "Increased bleeding risk."}
    assert calls["count"] == 1
