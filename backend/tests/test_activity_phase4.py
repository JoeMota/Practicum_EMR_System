"""Phase 4: active chart time, the student report, at-risk flags, delete, retrieve, and purge."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from openpyxl import load_workbook
import io

from app.models.user import User
from app.services.retention import purge_expired
from tests.test_chart_phase1 import CASE
from tests.test_workflows import course_id, login, patient_by_mrn


def _today() -> str:
    return datetime.now(ZoneInfo("America/Denver")).date().isoformat()


def _yesterday() -> str:
    return (datetime.now(ZoneInfo("America/Denver")).date() - timedelta(days=1)).isoformat()


async def _row(client, headers, course: str, role: str, user_id: str, start: str, end: str) -> dict:
    report = await client.get(
        f"/api/v1/reports/courses/{course}/activity",
        headers=headers,
        params={"role": role, "start": start, "end": end},
    )
    assert report.status_code == 200, report.text
    return next(item for item in report.json()["rows"] if item["userId"] == user_id)


@pytest.mark.asyncio
async def test_inactive_heartbeat_adds_no_time(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    student, me = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    created = await client.post(
        "/api/v1/cases", headers=instructor, params={"course_id": course, "role": "instructor"}, json=CASE
    )
    assert created.status_code == 200, created.text
    assigned = await client.post(
        "/api/v1/patients",
        headers=instructor,
        params={"course_id": course, "role": "instructor"},
        json={"sourcePatientId": created.json()["id"], "ownerId": me["user"]["id"]},
    )
    assert assigned.status_code == 200, assigned.text
    quiet = await client.post(
        f"/api/v1/patients/{assigned.json()['id']}/presence",
        headers=student,
        params={"role": "student"},
        json={"active": False},
    )
    assert quiet.status_code == 204, quiet.text
    before = await _row(client, instructor, course, "instructor", me["user"]["id"], _today(), _today())
    assert before["sessions"] == 0
    assert before["activeMinutes"] == 0

    beat = await client.post(
        f"/api/v1/patients/{assigned.json()['id']}/presence",
        headers=student,
        params={"role": "student"},
        json={"active": True},
    )
    assert beat.status_code == 204, beat.text
    after = await _row(client, instructor, course, "instructor", me["user"]["id"], _today(), _today())
    assert after["sessions"] == 1


@pytest.mark.asyncio
async def test_activity_report_uses_the_date_range(client):
    instructor, me = await login(client, "gerardo.sillas@utep.edu")
    student, student_session = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    created = await client.post(
        "/api/v1/cases", headers=instructor, params={"course_id": course, "role": "instructor"}, json=CASE
    )
    assigned = await client.post(
        "/api/v1/patients",
        headers=instructor,
        params={"course_id": course, "role": "instructor"},
        json={"sourcePatientId": created.json()["id"], "ownerId": student_session["user"]["id"]},
    )
    chart_id = assigned.json()["id"]
    opened = await client.get(f"/api/v1/patients/{chart_id}", headers=student, params={"role": "student"})
    assert opened.status_code == 200, opened.text
    note = await client.post(
        f"/api/v1/patients/{chart_id}/notes",
        headers=student,
        params={"role": "student"},
        json={"templateId": "general_soap", "discipline": "pharmacy"},
    )
    assert note.status_code == 200, note.text
    routed = await client.patch(
        f"/api/v1/notes/{note.json()['id']}",
        headers=student,
        params={"role": "student"},
        json={"expectedVersion": note.json()["version"], "routedToId": me["user"]["id"]},
    )
    assert routed.status_code == 200, routed.text
    signed = await client.post(
        f"/api/v1/notes/{note.json()['id']}/sign",
        headers=student,
        params={"role": "student"},
        json={"expectedVersion": routed.json()["version"]},
    )
    assert signed.status_code == 200, signed.text

    today = await _row(client, instructor, course, "instructor", student_session["user"]["id"], _today(), _today())
    assert today["chartsOpened"] == 1
    assert today["notesStarted"] == 1
    assert today["notesSubmitted"] == 1
    assert today["lastSignIn"]

    earlier = await _row(client, instructor, course, "instructor", student_session["user"]["id"], _yesterday(), _yesterday())
    assert earlier["chartsOpened"] == 0
    assert earlier["notesStarted"] == 0
    assert earlier["notesSubmitted"] == 0

    workbook = await client.get(
        f"/api/v1/reports/courses/{course}/activity.xlsx",
        headers=instructor,
        params={"role": "instructor", "start": _today(), "end": _today()},
    )
    assert workbook.status_code == 200, workbook.text
    sheet = load_workbook(io.BytesIO(workbook.content)).active
    assert sheet["A1"].value == "Course"
    assert sheet["E1"].value == "Active minutes"
    denied = await client.get(
        "/api/v1/reports/activity.xlsx",
        headers=student,
        params={"start": _today(), "end": _today()},
    )
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_at_risk_flags_idle_students_and_clears_after_a_submitted_note(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    student, me = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    imported = await client.post(
        f"/api/v1/courses/{course}/roster/import",
        headers=instructor,
        json={
            "discipline": "pharmacy",
            "role": "student",
            "rows": [{
                "fullName": "Idle Student",
                "email": "idle.student@miners.utep.edu",
                "universityId": "800111222",
                "problem": None,
            }],
        },
    )
    assert imported.status_code == 200, imported.text
    admin, _ = await login(client, "gerardo.sillas@utep.edu", role="admin")
    found = await client.get("/api/v1/users", headers=admin, params={"q": "idle.student"})
    assert found.status_code == 200, found.text
    idle_id = found.json()[0]["id"]

    before = await client.get(
        f"/api/v1/reports/courses/{course}/at-risk",
        headers=instructor,
        params={"role": "instructor"},
    )
    assert before.status_code == 200, before.text
    assert before.json()["days"] == 7
    idle = next(item for item in before.json()["students"] if item["userId"] == idle_id)
    assert "No chart activity for 7 days" in idle["reasons"]

    chart = await patient_by_mrn(client, student, course, "student", "TR-10021-DR")
    beat = await client.post(
        f"/api/v1/patients/{chart['id']}/presence",
        headers=student,
        params={"role": "student"},
        json={"active": True},
    )
    assert beat.status_code == 204, beat.text
    after = await client.get(
        f"/api/v1/reports/courses/{course}/at-risk",
        headers=instructor,
        params={"role": "instructor"},
    )
    assert all(item["userId"] != me["user"]["id"] for item in after.json()["students"]), after.text


@pytest.mark.asyncio
async def test_delete_anonymizes_login_and_keeps_the_note(client):
    admin, _ = await login(client, "gerardo.sillas@utep.edu", role="admin")
    instructor, _ = await login(client, "joe.mota@utep.edu")
    student, me = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, student, "PHAR 5320")
    chart = await patient_by_mrn(client, student, course, "student", "TR-10021-DR")
    notes = await client.get(
        f"/api/v1/patients/{chart['id']}/notes", headers=student, params={"role": "student"}
    )
    assert notes.status_code == 200, notes.text
    note_id = notes.json()[0]["id"]

    blocked = await client.post(
        f"/api/v1/users/{me['user']['id']}/delete",
        headers=instructor,
        json={"email": me["user"]["email"]},
    )
    assert blocked.status_code == 403

    mismatch = await client.post(
        f"/api/v1/users/{me['user']['id']}/delete",
        headers=admin,
        json={"email": "someone.else@utep.edu"},
    )
    assert mismatch.status_code == 400

    deleted = await client.post(
        f"/api/v1/users/{me['user']['id']}/delete",
        headers=admin,
        json={"email": me["user"]["email"]},
    )
    assert deleted.status_code == 200, deleted.text
    login_again = await client.post(
        "/api/v1/auth/login",
        data={"username": "daniel.reyes@miners.utep.edu", "password": "practicum-demo"},
    )
    assert login_again.status_code == 401
    kept = await client.get(f"/api/v1/notes/{note_id}", headers=admin, params={"role": "admin"})
    assert kept.status_code == 200, kept.text
    assert kept.json()["id"] == note_id
    roster = await client.get(f"/api/v1/courses/{course}/roster", headers=admin)
    assert roster.status_code == 200, roster.text
    assert all(item["id"] != me["user"]["id"] for item in roster.json())


@pytest.mark.asyncio
async def test_retrieve_makes_an_archived_course_active(client):
    admin, _ = await login(client, "gerardo.sillas@utep.edu", role="admin")
    created = await client.post(
        "/api/v1/courses",
        headers=admin,
        json={"code": "TEST 4100", "title": "Retrieve", "term": "Fall 2026"},
    )
    assert created.status_code == 201, created.text
    course_id_value = created.json()["id"]
    assert created.json()["inactivityDays"] == 7
    for next_status in ("active", "ended", "archived"):
        changed = await client.post(
            f"/api/v1/courses/{course_id_value}/status",
            headers=admin,
            json={"status": next_status},
        )
        assert changed.status_code == 200, changed.text
    retrieved = await client.post(
        f"/api/v1/courses/{course_id_value}/status",
        headers=admin,
        json={"status": "active"},
    )
    assert retrieved.status_code == 200, retrieved.text
    assert retrieved.json()["status"] == "active"
    window = await client.patch(
        f"/api/v1/courses/{course_id_value}/inactivity-days",
        headers=admin,
        json={"days": 14},
    )
    assert window.status_code == 200, window.text
    assert window.json()["inactivityDays"] == 14
    instructor, _ = await login(client, "joe.mota@utep.edu")
    blocked = await client.patch(
        f"/api/v1/courses/{course_id_value}/inactivity-days",
        headers=instructor,
        json={"days": 3},
    )
    assert blocked.status_code == 403


@pytest.mark.asyncio
async def test_startup_purge_anonymizes_only_accounts_older_than_two_years(client, db_session):
    admin, _ = await login(client, "clarissa.dominguez@utep.edu")
    course = await course_id(client, admin, "PHAR 5320")
    imported = await client.post(
        f"/api/v1/courses/{course}/roster/import",
        headers=admin,
        json={
            "discipline": "pharmacy",
            "role": "student",
            "rows": [
                {"fullName": "Old Archive", "email": "old.archive@miners.utep.edu", "universityId": "800111001", "problem": None},
                {"fullName": "New Archive", "email": "new.archive@miners.utep.edu", "universityId": "800111002", "problem": None},
            ],
        },
    )
    assert imported.status_code == 200, imported.text
    people = await client.get("/api/v1/users", headers=admin, params={"q": "archive@"})
    assert people.status_code == 200, people.text
    by_email = {item["email"]: item["id"] for item in people.json()}
    for user_id in by_email.values():
        archived = await client.post(f"/api/v1/users/{user_id}/archive", headers=admin)
        assert archived.status_code == 200, archived.text
    old = await db_session.get(User, by_email["old.archive@miners.utep.edu"])
    old.archived_at = datetime.now(timezone.utc) - timedelta(days=800)
    await db_session.flush()

    count = await purge_expired(db_session)
    await db_session.flush()
    await db_session.refresh(old)
    assert count == 1
    assert old.email == f"archived-{old.id}@invalid.local"
    assert old.is_active is False
    recent = await db_session.get(User, by_email["new.archive@miners.utep.edu"])
    await db_session.refresh(recent)
    assert recent.email == "new.archive@miners.utep.edu"
    assert recent.purged_at is None
