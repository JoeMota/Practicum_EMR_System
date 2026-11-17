"""Insurance authoring and read-only chart serialization coverage."""

import pytest

from tests.test_sprint3 import DEMO_CASE
from tests.test_workflows import course_id, login


@pytest.mark.asyncio
async def test_case_insurance_round_trips_and_is_copied_to_student_chart(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    student, student_session = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    body = {
        **DEMO_CASE,
        "insurancePayer": "Example Health Plan",
        "insuranceMemberId": "MEM-123",
        "insuranceGroupNumber": "GRP-9",
        "insuranceNotes": "Prior authorization required for imaging.",
    }

    created = await client.post(
        "/api/v1/cases", headers=instructor, params={"course_id": course, "role": "instructor"}, json=body,
    )
    assert created.status_code == 200, created.text
    case = created.json()
    assert case["insurance"] == {
        "payer": "Example Health Plan",
        "memberId": "MEM-123",
        "groupNumber": "GRP-9",
        "notes": "Prior authorization required for imaging.",
    }

    body["insuranceNotes"] = "Authorization approved for this scenario."
    updated = await client.patch(
        f"/api/v1/cases/{case['id']}", headers=instructor, params={"role": "instructor"}, json=body,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["insurance"]["notes"] == "Authorization approved for this scenario."

    assigned = await client.post(
        "/api/v1/patients",
        headers=instructor,
        params={"course_id": course, "role": "instructor"},
        json={"sourcePatientId": case["id"], "ownerId": student_session["user"]["id"]},
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["insurance"]["notes"] == "Authorization approved for this scenario."

    chart = await client.get(
        f"/api/v1/patients/{assigned.json()['id']}", headers=student, params={"role": "student"},
    )
    assert chart.status_code == 200, chart.text
    assert chart.json()["insurance"]["payer"] == "Example Health Plan"
    assert chart.json()["insurance"]["memberId"] == "MEM-123"
    assert chart.json()["insurance"]["groupNumber"] == "GRP-9"
    assert chart.json()["insurance"]["notes"] == "Authorization approved for this scenario."
