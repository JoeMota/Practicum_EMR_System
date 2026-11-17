"""CASE-05 / REV-07: release after cosign lets the student read the key."""

import uuid

import pytest
from sqlalchemy import select

from app.models.audit import AuditEvent
from app.models.clinical import Patient
from tests.test_workflows import course_id, login


@pytest.mark.asyncio
async def test_student_reads_answer_key_only_after_release_and_cosign(client, db_session):
    instructor, instructor_session = await login(client, "gerardo.sillas@utep.edu")
    student, me = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    masters = await client.get("/api/v1/cases", headers=instructor, params={"course_id": course, "role": "instructor"})
    master = next(row for row in masters.json() if row["mrn"] == "CASE-10001")
    assigned = await client.post(
        "/api/v1/patients",
        headers=instructor,
        params={"course_id": course, "role": "instructor"},
        json={"sourcePatientId": master["id"], "ownerId": me["user"]["id"]},
    )
    assert assigned.status_code == 200, assigned.text
    copy_id = assigned.json()["id"]

    blocked = await client.get(f"/api/v1/patients/{copy_id}/answer-key", headers=student, params={"role": "student"})
    assert blocked.status_code == 403

    created = await client.post(
        f"/api/v1/patients/{copy_id}/notes",
        headers=student,
        params={"role": "student"},
        json={"templateId": "pharmacy_mtm", "discipline": "pharmacy"},
    )
    assert created.status_code == 200, created.text
    note_id = created.json()["id"]
    routed = await client.patch(
        f"/api/v1/notes/{note_id}",
        headers=student,
        params={"role": "student"},
        json={"expectedVersion": created.json()["version"], "routedToId": instructor_session["user"]["id"]},
    )
    assert routed.status_code == 200, routed.text
    signed = await client.post(
        f"/api/v1/notes/{note_id}/sign",
        headers=student,
        params={"role": "student"},
        json={"expectedVersion": routed.json()["version"]},
    )
    assert signed.status_code == 200, signed.text
    cosigned = await client.post(
        f"/api/v1/notes/{note_id}/cosign",
        headers=instructor,
        params={"role": "instructor"},
        json={"comment": "Looks good."},
    )
    assert cosigned.status_code == 200, cosigned.text

    still_blocked = await client.get(f"/api/v1/patients/{copy_id}/answer-key", headers=student, params={"role": "student"})
    assert still_blocked.status_code == 403

    released = await client.post(
        f"/api/v1/patients/{copy_id}/answer-key/release",
        headers=instructor,
        params={"role": "instructor"},
    )
    assert released.status_code == 200, released.text
    stored = await db_session.get(Patient, uuid.UUID(copy_id))
    assert stored.answer_key_released_at is not None

    allowed = await client.get(f"/api/v1/patients/{copy_id}/answer-key", headers=student, params={"role": "student"})
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["diagnoses"]
    events = (
        await db_session.scalars(
            select(AuditEvent).where(AuditEvent.entity_id == copy_id, AuditEvent.action == "answer_key.release")
        )
    ).all()
    assert events
