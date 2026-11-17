"""Medication fill verification: submit → verify/hold → release."""

import pytest

from tests.test_chart_phase1 import _assigned_chart
from tests.test_workflows import course_id, login


@pytest.mark.asyncio
async def test_student_submit_instructor_verify_hold_and_release(client):
    instructor, student, chart = await _assigned_chart(client)
    med_id = chart["medications"][0]["id"]

    denied = await client.post(
        f"/api/v1/patients/medication-orders/00000000-0000-0000-0000-000000000001/review",
        headers=student,
        params={"role": "student"},
        json={"decision": "verify"},
    )
    assert denied.status_code in {403, 404}

    submitted = await client.post(
        f"/api/v1/patients/{chart['id']}/medication-orders",
        headers=student,
        params={"role": "student"},
        json={"medicationId": med_id, "quantity": "30 tablets"},
    )
    assert submitted.status_code == 200, submitted.text
    order = submitted.json()
    assert order["status"] == "pending_verify"
    assert order["sig"] == "10 mg PO QD"
    assert order["quantity"] == "30 tablets"

    duplicate = await client.post(
        f"/api/v1/patients/{chart['id']}/medication-orders",
        headers=student,
        params={"role": "student"},
        json={"medicationId": med_id},
    )
    assert duplicate.status_code == 409

    student_verify = await client.post(
        f"/api/v1/patients/medication-orders/{order['id']}/review",
        headers=student,
        params={"role": "student"},
        json={"decision": "verify"},
    )
    assert student_verify.status_code == 403

    held = await client.post(
        f"/api/v1/patients/medication-orders/{order['id']}/review",
        headers=instructor,
        params={"role": "instructor"},
        json={"decision": "hold", "comment": "Confirm indication"},
    )
    assert held.status_code == 200, held.text
    assert held.json()["status"] == "held"
    assert held.json()["reviewComment"] == "Confirm indication"

    resubmitted = await client.post(
        f"/api/v1/patients/medication-orders/{order['id']}/review",
        headers=student,
        params={"role": "student"},
        json={"decision": "resubmit"},
    )
    assert resubmitted.status_code == 200, resubmitted.text
    assert resubmitted.json()["status"] == "pending_verify"

    verified = await client.post(
        f"/api/v1/patients/medication-orders/{order['id']}/review",
        headers=instructor,
        params={"role": "instructor"},
        json={"decision": "verify"},
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["status"] == "verified"

    released = await client.post(
        f"/api/v1/patients/medication-orders/{order['id']}/review",
        headers=instructor,
        params={"role": "instructor"},
        json={"decision": "release"},
    )
    assert released.status_code == 200, released.text
    assert released.json()["status"] == "released"

    listed = await client.get(
        f"/api/v1/patients/{chart['id']}/medication-orders",
        headers=student,
        params={"role": "student"},
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()[0]["status"] == "released"


@pytest.mark.asyncio
async def test_inactive_medication_cannot_be_submitted(client):
    instructor, student, chart = await _assigned_chart(client)
    med_id = chart["medications"][0]["id"]
    stopped = await client.post(
        f"/api/v1/patients/{chart['id']}/medications/{med_id}/discontinue",
        headers=student,
        params={"role": "student"},
    )
    assert stopped.status_code == 200, stopped.text
    denied = await client.post(
        f"/api/v1/patients/{chart['id']}/medication-orders",
        headers=student,
        params={"role": "student"},
        json={"medicationId": med_id},
    )
    assert denied.status_code == 409
