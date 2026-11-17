import uuid

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models.audit import AuditEvent
from app.models.user import Role, User
from app.services.hidden import assert_no_hidden
from tests.test_workflows import course_id, login, patient_by_mrn


@pytest.mark.asyncio
async def test_seeded_demo_patient_can_sign_in_and_view_portal(client):
    headers, _ = await login(client, "patient.demo@example.com")

    response = await client.get("/api/v1/portal", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["patient"]["mrn"] == "TR-20001"
    assert response.json()["labs"]


@pytest.mark.asyncio
async def test_portal_returns_only_linked_chart_sorted_and_audits_success(client, db_session):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    rosa = await patient_by_mrn(client, instructor, course, "instructor", "TR-20001")
    headers, portal_user = await _portal_headers(client, db_session, rosa["id"], "linked")

    response = await client.get("/api/v1/portal", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["patient"]["mrn"] == "TR-20001"
    assert body["patient"]["name"]
    assert body["last_visit"]["date"]
    assert body["last_visit"]["type"]
    assert body["medication_list"]
    assert body["prescribed_medications"] == [item for item in body["medication_list"] if item["prescribed"]]
    assert body["labs"]

    labs_by_name = sorted(body["labs"], key=lambda item: item["name"].casefold())
    expected_labs = sorted(labs_by_name, key=lambda item: item["collected_at"], reverse=True)
    assert body["labs"] == expected_labs
    assert_no_hidden(body)

    event = await db_session.scalar(
        select(AuditEvent).where(
            AuditEvent.action == "portal.view",
            AuditEvent.entity_id == rosa["id"],
            AuditEvent.actor_user_id == portal_user.id,
        )
    )
    assert event is not None
    assert event.entity_type == "patient"
    assert event.course_id == uuid.UUID(course)
    assert event.result == "ok"
    assert event.ip_address == "127.0.0.1"


@pytest.mark.asyncio
async def test_portal_isolates_linked_charts_and_unlinked_login_is_not_found(client, db_session):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    rosa = await patient_by_mrn(client, instructor, course, "instructor", "TR-20001")
    elena = await patient_by_mrn(client, instructor, course, "instructor", "TR-20003")
    rosa_headers, _ = await _portal_headers(client, db_session, rosa["id"], "rosa")
    elena_headers, _ = await _portal_headers(client, db_session, elena["id"], "elena")
    unlinked_headers, unlinked_user = await _portal_headers(client, db_session, None, "unlinked")

    rosa_response = await client.get("/api/v1/portal", headers=rosa_headers)
    elena_response = await client.get("/api/v1/portal", headers=elena_headers)
    assert rosa_response.status_code == elena_response.status_code == 200
    assert rosa_response.json()["patient"]["mrn"] == "TR-20001"
    assert elena_response.json()["patient"]["mrn"] == "TR-20003"
    assert "TR-20003" not in str(rosa_response.json())
    assert "TR-20001" not in str(elena_response.json())
    assert (await client.get("/api/v1/portal", headers=unlinked_headers)).status_code == 404
    assert await db_session.scalar(
        select(AuditEvent).where(
            AuditEvent.action == "portal.view",
            AuditEvent.actor_user_id == unlinked_user.id,
        )
    ) is None


@pytest.mark.asyncio
async def test_student_and_instructor_are_denied_without_portal_view_audit(client, db_session):
    student, _ = await login(client, "daniel.reyes@miners.utep.edu")
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    for headers in (student, instructor):
        response = await client.get("/api/v1/portal", headers=headers)
        assert response.status_code == 403

    events = (await db_session.scalars(select(AuditEvent).where(AuditEvent.action == "portal.view"))).all()
    assert events == []


@pytest.mark.asyncio
async def test_portal_rejects_write_methods(client, db_session):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    rosa = await patient_by_mrn(client, instructor, course, "instructor", "TR-20001")
    headers, _ = await _portal_headers(client, db_session, rosa["id"], "readonly")

    for method in ("post", "put", "patch", "delete"):
        response = await client.request(method.upper(), "/api/v1/portal", headers=headers, json={})
        assert response.status_code in (404, 405)


async def _portal_headers(client, db_session, patient_id, suffix: str):
    role = await db_session.scalar(select(Role).where(Role.code == "patient"))
    user = User(
        email=f"portal-{suffix}@utep.edu",
        first_name="Portal",
        last_name="Patient",
        hashed_password=hash_password("portal-test-password"),
        must_change_password=False,
        is_active=True,
        portal_patient_id=patient_id,
        roles=[role],
    )
    db_session.add(user)
    await db_session.flush()
    headers, _ = await login(client, user.email, "portal-test-password")
    return headers, user
