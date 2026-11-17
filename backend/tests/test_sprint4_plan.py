"""Protected notes, sessions, dose flags, portal coverage, and assist."""

import uuid

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.clinical import ClinicalNote, CourseMembership
from app.models.user import Discipline, Role, User
from app.services.dose_check import check_dose, check_text
from tests.test_portal import _portal_headers
from tests.test_workflows import course_id, login, patient_by_mrn


def test_dose_parser_covers_units_and_the_ten_thousand_edge():
    assert check_dose("10 mg", "lisinopril") == []
    assert check_dose("10mg", "lisinopril") == []
    assert check_dose("10,000 mg", "lisinopril")[0]["code"] == "dose_extreme"
    assert any(flag["code"] == "dose_extreme" for flag in check_dose("10000 mg", "acetaminophen"))
    assert check_dose("10", "lisinopril")[0]["code"] == "missing_unit"
    assert any(flag["code"] == "unit_mismatch" for flag in check_dose("10 mg", "levothyroxine"))
    assert check_text("Takes doses as scheduled.", ["lisinopril"]) == []
    assert any(flag["code"] == "dose_extreme" for flag in check_text("Increase lisinopril to 10000 mg.", ["Lisinopril"]))


@pytest.mark.asyncio
async def test_psychiatry_note_is_hidden_encrypted_and_discipline_scoped(client, db_session):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    student, _ = await login(client, "daniel.reyes@miners.utep.edu")
    other, _ = await login(client, "joe.mota@utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    created = await client.post(
        "/api/v1/note-templates",
        headers=instructor,
        params={"role": "instructor"},
        json={
            "name": "Psychiatry check-in",
            "discipline": "pharmacy",
            "courseId": course,
            "sensitivity": "psychiatry",
            "sections": [{"id": "N", "title": "Note", "fields": [{"id": "body", "label": "Private note", "kind": "textarea"}]}],
        },
    )
    assert created.status_code == 200, created.text
    chart = await patient_by_mrn(client, student, course, "student", "TR-10021-DR")
    note = await client.post(
        f"/api/v1/patients/{chart['id']}/notes",
        headers=student,
        params={"role": "student"},
        json={"templateId": created.json()["id"], "discipline": "pharmacy"},
    )
    assert note.status_code == 200, note.text
    note_id = note.json()["id"]
    edited = await client.patch(
        f"/api/v1/notes/{note_id}",
        headers=student,
        params={"role": "student"},
        json={"expectedVersion": note.json()["version"], "content": {"body": "private psychiatry text"}},
    )
    assert edited.status_code == 200, edited.text
    stored = await db_session.get(ClinicalNote, uuid.UUID(note_id))
    await db_session.refresh(stored)
    assert stored is not None
    assert stored.content == {}
    assert stored.content_cipher
    assert "private psychiatry text" not in stored.content_cipher

    hidden = await client.get(f"/api/v1/notes/{note_id}", headers=student, params={"role": "student"})
    assert hidden.status_code == 404
    listed = await client.get(f"/api/v1/patients/{chart['id']}/notes", headers=student, params={"role": "student"})
    assert note_id not in listed.text

    opened = await client.get(f"/api/v1/notes/{note_id}", headers=instructor, params={"role": "instructor"})
    assert opened.status_code == 200, opened.text
    audit = await client.get("/api/v1/audit", headers=instructor, params={"course_id": course, "role": "instructor"})
    actions = {row["action"] for row in audit.json() if note_id in row["entity"]}
    assert "note.view_psychiatry" in actions
    assert "note.view_sensitive" in actions

    joe = await db_session.scalar(select(User).where(User.email == "joe.mota@utep.edu"))
    nursing = await db_session.scalar(select(Discipline).where(Discipline.code == "nursing"))
    instructor_role = await db_session.scalar(select(Role).where(Role.code == "instructor"))
    seat = await db_session.scalar(
        select(CourseMembership).where(
            CourseMembership.user_id == joe.id,
            CourseMembership.course_id == uuid.UUID(course),
            CourseMembership.role_id == instructor_role.id,
        )
    )
    assert seat is not None and nursing is not None
    seat.discipline_id = nursing.id
    seat.discipline = nursing
    await db_session.commit()
    denied = await client.get(f"/api/v1/notes/{note_id}", headers=other, params={"role": "instructor"})
    assert denied.status_code == 404


@pytest.mark.asyncio
async def test_login_locks_after_five_failures_and_logout_revokes_refresh(client):
    for _ in range(4):
        failed = await client.post(
            "/api/v1/auth/login",
            data={"username": "daniel.reyes@miners.utep.edu", "password": "wrong-password"},
        )
        assert failed.status_code == 401
    locked = await client.post(
        "/api/v1/auth/login",
        data={"username": "daniel.reyes@miners.utep.edu", "password": "wrong-password"},
    )
    assert locked.status_code == 423
    still = await client.post(
        "/api/v1/auth/login",
        data={"username": "daniel.reyes@miners.utep.edu", "password": "practicum-demo"},
    )
    assert still.status_code == 423

    headers, body = await login(client, "gerardo.sillas@utep.edu")
    assert body["refresh_token"]
    goodbye = await client.post("/api/v1/auth/logout", json={"refreshToken": body["refresh_token"]})
    assert goodbye.status_code == 204, goodbye.text
    reused = await client.post("/api/v1/auth/refresh", json={"refreshToken": body["refresh_token"]})
    assert reused.status_code == 401
    assert headers["Authorization"]


@pytest.mark.asyncio
async def test_dose_flags_follow_the_course_mode(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    admin, _ = await login(client, "gerardo.sillas@utep.edu", role="admin")
    student, _ = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    chart = await patient_by_mrn(client, student, course, "student", "TR-10021-DR")
    saved = await client.post(
        f"/api/v1/patients/{chart['id']}/medications",
        headers=student,
        params={"role": "student"},
        json={"name": "Lisinopril", "dose": "10000 mg", "route": "oral", "frequency": "once"},
    )
    assert saved.status_code == 200, saved.text
    flags = next(item["flags"] for item in saved.json()["medications"] if item["dose"] == "10000 mg")
    assert any(flag["code"] == "dose_extreme" for flag in flags)

    blocked_mode = await client.patch(
        f"/api/v1/courses/{course}/policy",
        headers=admin,
        json={"guardrailMode": "block"},
    )
    assert blocked_mode.status_code == 200, blocked_mode.text
    blocked = await client.post(
        f"/api/v1/patients/{chart['id']}/medications",
        headers=student,
        params={"role": "student"},
        json={"name": "Lisinopril", "dose": "10000 mg", "route": "oral", "frequency": "once"},
    )
    assert blocked.status_code == 422

    ack_mode = await client.patch(
        f"/api/v1/courses/{course}/policy",
        headers=admin,
        json={"guardrailMode": "acknowledge"},
    )
    assert ack_mode.status_code == 200, ack_mode.text
    unconfirmed = await client.post(
        f"/api/v1/patients/{chart['id']}/medications",
        headers=student,
        params={"role": "student"},
        json={"name": "Lisinopril", "dose": "10000 mg", "route": "oral", "frequency": "once"},
    )
    assert unconfirmed.status_code == 422
    confirmed = await client.post(
        f"/api/v1/patients/{chart['id']}/medications",
        headers=student,
        params={"role": "student"},
        json={
            "name": "Lisinopril",
            "dose": "10000 mg",
            "route": "oral",
            "frequency": "once",
            "acknowledgedFlags": ["dose_extreme"],
        },
    )
    assert confirmed.status_code == 200, confirmed.text


@pytest.mark.asyncio
async def test_portal_lists_coverage_and_cpt_search_omits_deleted_telehealth(client, db_session):
    admin, _ = await login(client, "gerardo.sillas@utep.edu", role="admin")
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    rosa = await patient_by_mrn(client, instructor, course, "instructor", "TR-20001")
    headers, _ = await _portal_headers(client, db_session, rosa["id"], "coverage")
    portal = await client.get("/api/v1/portal", headers=headers)
    assert portal.status_code == 200, portal.text
    assert "insurance" in portal.json()
    search = await client.get("/api/v1/reference/cpt", headers=admin, params={"q": "99441"})
    assert search.status_code == 200, search.text
    assert all(row["code"] != "99441" for row in search.json())


@pytest.mark.asyncio
async def test_assist_stays_off_for_protected_notes_and_does_not_save(client, monkeypatch):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    admin, _ = await login(client, "gerardo.sillas@utep.edu", role="admin")
    student, _ = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    chart = await patient_by_mrn(client, student, course, "student", "TR-10021-DR")
    draft = await client.post(
        f"/api/v1/patients/{chart['id']}/notes",
        headers=student,
        params={"role": "student"},
        json={"templateId": "pharmacy_soap", "discipline": "pharmacy"},
    )
    assert draft.status_code == 200, draft.text
    note_id = draft.json()["id"]
    calls = {"count": 0}

    async def fake_suggest(section_id, context):
        calls["count"] += 1
        return "A teaching suggestion."

    from app.api.routes import notes as notes_route

    monkeypatch.setattr(notes_route, "suggest_section", fake_suggest)
    monkeypatch.setattr(settings, "AI_API_URL", "http://assist.example")
    off = await client.post(
        f"/api/v1/notes/{note_id}/suggest",
        headers=student,
        params={"role": "student"},
        json={"sectionId": "S"},
    )
    assert off.status_code == 409
    assert calls["count"] == 0

    enabled = await client.patch(f"/api/v1/courses/{course}/policy", headers=admin, json={"aiAssist": True})
    assert enabled.status_code == 200, enabled.text
    suggested = await client.post(
        f"/api/v1/notes/{note_id}/suggest",
        headers=student,
        params={"role": "student"},
        json={"sectionId": "S"},
    )
    assert suggested.status_code == 200, suggested.text
    assert suggested.json()["suggestion"] == "A teaching suggestion."
    assert calls["count"] == 1
    again = await client.get(f"/api/v1/notes/{note_id}", headers=student, params={"role": "student"})
    assert "A teaching suggestion." not in again.text

    private = await client.post(
        "/api/v1/note-templates",
        headers=instructor,
        params={"role": "instructor"},
        json={
            "name": "Psychiatry assist",
            "discipline": "pharmacy",
            "courseId": course,
            "sensitivity": "psychiatry",
            "sections": [{"id": "N", "title": "Note", "fields": [{"id": "body", "label": "Private", "kind": "textarea"}]}],
        },
    )
    assert private.status_code == 200, private.text
    hidden = await client.post(
        f"/api/v1/patients/{chart['id']}/notes",
        headers=student,
        params={"role": "student"},
        json={"templateId": private.json()["id"], "discipline": "pharmacy"},
    )
    assert hidden.status_code == 200, hidden.text
    refused = await client.post(
        f"/api/v1/notes/{hidden.json()['id']}/suggest",
        headers=student,
        params={"role": "student"},
        json={"sectionId": "N"},
    )
    assert refused.status_code == 404
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_intro_course_is_seeded_and_provider_flag_is_separate(client):
    admin, _ = await login(client, "gerardo.sillas@utep.edu", role="admin")
    listed = await client.get("/api/v1/courses", headers=admin)
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    intro = next(row for row in rows if row["code"] == "PHAR 5101")
    practicum = next(row for row in rows if row["code"] == "PHAR 5320")
    assert intro["title"] == "Intro to Pharmacy"
    assert intro["guardrailProfile"] == "intro_pharmacy"
    assert practicum["guardrailProfile"] == "practicum"
    assert intro["aiProviderConfigured"] is False
    assert practicum["aiAssist"] is False


@pytest.mark.asyncio
async def test_inserted_text_runs_the_course_dose_flags(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    admin, _ = await login(client, "gerardo.sillas@utep.edu", role="admin")
    student, _ = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    chart = await patient_by_mrn(client, student, course, "student", "TR-10021-DR")
    draft = await client.post(
        f"/api/v1/patients/{chart['id']}/notes",
        headers=student,
        params={"role": "student"},
        json={"templateId": "pharmacy_soap", "discipline": "pharmacy"},
    )
    assert draft.status_code == 200, draft.text
    note_id = draft.json()["id"]
    body = {"text": "Increase lisinopril to 10000 mg today."}

    advisory = await client.post(
        f"/api/v1/notes/{note_id}/dose-check", headers=student, params={"role": "student"}, json=body,
    )
    assert advisory.status_code == 200, advisory.text
    assert any(flag["code"] == "dose_extreme" for flag in advisory.json()["flags"])
    assert advisory.json()["blocked"] is False
    assert advisory.json()["needsAcknowledgement"] is False

    blocked = await client.patch(
        f"/api/v1/courses/{course}/policy", headers=admin, json={"guardrailMode": "block"},
    )
    assert blocked.status_code == 200, blocked.text
    refused = await client.post(
        f"/api/v1/notes/{note_id}/dose-check", headers=student, params={"role": "student"}, json=body,
    )
    assert refused.status_code == 200, refused.text
    assert refused.json()["blocked"] is True

    acknowledge = await client.patch(
        f"/api/v1/courses/{course}/policy", headers=admin, json={"guardrailMode": "acknowledge"},
    )
    assert acknowledge.status_code == 200, acknowledge.text
    pending = await client.post(
        f"/api/v1/notes/{note_id}/dose-check", headers=student, params={"role": "student"}, json=body,
    )
    assert pending.json()["needsAcknowledgement"] is True
    accepted = await client.post(
        f"/api/v1/notes/{note_id}/dose-check",
        headers=student,
        params={"role": "student"},
        json={**body, "acknowledgedFlags": ["dose_extreme"]},
    )
    assert accepted.json()["needsAcknowledgement"] is False
    assert accepted.json()["blocked"] is False
