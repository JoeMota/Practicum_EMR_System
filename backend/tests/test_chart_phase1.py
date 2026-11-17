"""Phase 1 chart: vitals history, allergy reaction, medication fields, and Roomed."""

import pytest

from tests.test_workflows import course_id, login

CASE = {
    "firstName": "Elena",
    "lastName": "Vasquez",
    "dob": "1988-03-14",
    "sexAtBirth": "Female",
    "chiefComplaint": "Follow-up",
    "hpi": "Here for a blood pressure check.",
    "pastMedicalHistory": "Hypertension.",
    "surgicalHistory": "None.",
    "familyHistory": "None.",
    "socialHistory": "No tobacco.",
    "encounterType": "Office visit",
    "careSetting": "Outpatient",
    "lifecycle": "Active",
    "encounterStatus": "Checked in",
    "medications": [{"name": "Lisinopril", "dose": "10 mg", "route": "PO", "frequency": "daily"}],
}


async def _assigned_chart(client, *, locks: dict | None = None):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    student, me = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    body = dict(CASE)
    if locks is not None:
        body["sectionLocks"] = locks
    created = await client.post(
        "/api/v1/cases",
        headers=instructor,
        params={"course_id": course, "role": "instructor"},
        json=body,
    )
    assert created.status_code == 200, created.text
    assigned = await client.post(
        "/api/v1/patients",
        headers=instructor,
        params={"course_id": course, "role": "instructor"},
        json={"sourcePatientId": created.json()["id"], "ownerId": me["user"]["id"]},
    )
    assert assigned.status_code == 200, assigned.text
    return instructor, student, assigned.json()


@pytest.mark.asyncio
async def test_vitals_append_and_hide_entered_in_error_from_students(client):
    instructor, student, chart = await _assigned_chart(client)
    first = await client.post(
        f"/api/v1/patients/{chart['id']}/vitals",
        headers=student,
        params={"role": "student"},
        json={"label": "Pain", "value": "3"},
    )
    assert first.status_code == 200, first.text
    second = await client.post(
        f"/api/v1/patients/{chart['id']}/vitals",
        headers=student,
        params={"role": "student"},
        json={"label": "Pain", "value": "8"},
    )
    assert second.status_code == 200, second.text
    pains = [item for item in second.json()["vitals"] if item["label"] == "Pain"]
    assert [item["value"] for item in pains] == ["3", "8"]
    assert all(item["recordedByName"] for item in pains)
    assert all(item["recordedAt"] for item in pains)

    hidden = await client.post(
        f"/api/v1/patients/{chart['id']}/vitals/{pains[0]['id']}/entered-in-error",
        headers=student,
        params={"role": "student"},
    )
    assert hidden.status_code == 200, hidden.text
    assert [item["value"] for item in hidden.json()["vitals"] if item["label"] == "Pain"] == ["8"]

    staff = await client.get(
        f"/api/v1/patients/{chart['id']}",
        headers=instructor,
        params={"role": "instructor"},
    )
    assert staff.status_code == 200, staff.text
    marked = next(item for item in staff.json()["vitals"] if item["id"] == pains[0]["id"])
    assert marked["status"] == "entered_in_error"
    assert marked["value"] == "3"


@pytest.mark.asyncio
async def test_locked_vitals_reject_a_student_and_allow_an_instructor(client):
    instructor, student, chart = await _assigned_chart(client, locks={"vitals": True})
    denied = await client.post(
        f"/api/v1/patients/{chart['id']}/vitals",
        headers=student,
        params={"role": "student"},
        json={"label": "Pain", "value": "4"},
    )
    assert denied.status_code == 403
    allowed = await client.post(
        f"/api/v1/patients/{chart['id']}/vitals",
        headers=instructor,
        params={"role": "instructor"},
        json={"label": "Pain", "value": "4"},
    )
    assert allowed.status_code == 200, allowed.text
    assert any(item["label"] == "Pain" and item["value"] == "4" for item in allowed.json()["vitals"])


@pytest.mark.asyncio
async def test_student_can_record_bp_and_lung_sounds(client):
    """P1-4 / P1-5: unlocked assessment charts accept BP and lung-sound entries."""
    _instructor, student, chart = await _assigned_chart(client)
    bp = await client.post(
        f"/api/v1/patients/{chart['id']}/vitals",
        headers=student,
        params={"role": "student"},
        json={"label": "BP", "value": "128/82 mmHg"},
    )
    assert bp.status_code == 200, bp.text
    assert any(item["label"] == "BP" and item["value"] == "128/82 mmHg" for item in bp.json()["vitals"])

    lung = await client.post(
        f"/api/v1/patients/{chart['id']}/lung-sounds",
        headers=student,
        params={"role": "student"},
        json={"location": "RLL", "finding": "crackles", "notes": "Bases"},
    )
    assert lung.status_code == 200, lung.text
    rows = lung.json()["lungSounds"]
    assert any(item["location"] == "RLL" and item["finding"] == "crackles" for item in rows)
    sound = next(item for item in rows if item["location"] == "RLL")
    hidden = await client.post(
        f"/api/v1/patients/{chart['id']}/lung-sounds/{sound['id']}/entered-in-error",
        headers=student,
        params={"role": "student"},
    )
    assert hidden.status_code == 200, hidden.text
    assert all(item["location"] != "RLL" for item in hidden.json()["lungSounds"])


@pytest.mark.asyncio
async def test_locked_lung_sounds_reject_a_student(client):
    instructor, student, chart = await _assigned_chart(client, locks={"lung_sounds": True})
    denied = await client.post(
        f"/api/v1/patients/{chart['id']}/lung-sounds",
        headers=student,
        params={"role": "student"},
        json={"location": "RUL", "finding": "clear"},
    )
    assert denied.status_code == 403
    allowed = await client.post(
        f"/api/v1/patients/{chart['id']}/lung-sounds",
        headers=instructor,
        params={"role": "instructor"},
        json={"location": "RUL", "finding": "clear"},
    )
    assert allowed.status_code == 200, allowed.text


@pytest.mark.asyncio
async def test_compound_medication_and_sig_round_trip(client):
    _instructor, student, chart = await _assigned_chart(client)
    created = await client.post(
        f"/api/v1/patients/{chart['id']}/medications",
        headers=student,
        params={"role": "student"},
        json={
            "name": "Omeprazole (compounded)",
            "dose": "20 mg",
            "route": "PO",
            "frequency": "Once daily",
            "indication": "GERD",
            "isCompound": True,
            "compoundIngredients": "Omeprazole 20 mg",
            "compoundVehicle": "Gluten-free capsule",
            "compoundReason": "Celiac disease — avoid commercial capsules.",
        },
    )
    assert created.status_code == 200, created.text
    med = next(item for item in created.json()["medications"] if item["name"].startswith("Omeprazole"))
    assert med["sig"] == "20 mg PO QD"
    assert med["isCompound"] is True
    assert med["compoundVehicle"] == "Gluten-free capsule"
    assert "Celiac" in med["compoundReason"]


@pytest.mark.asyncio
async def test_allergy_reaction_medication_fields_and_roomed_status(client):
    _instructor, student, chart = await _assigned_chart(client)
    allergy = await client.post(
        f"/api/v1/patients/{chart['id']}/allergies",
        headers=student,
        params={"role": "student"},
        json={"substance": "Peanuts", "category": "food", "reaction": "hives"},
    )
    assert allergy.status_code == 200, allergy.text
    saved = next(item for item in allergy.json()["allergies"] if item["substance"] == "Peanuts")
    assert saved["reaction"] == "hives"
    assert saved["category"] == "food"

    medication = await client.post(
        f"/api/v1/patients/{chart['id']}/medications",
        headers=student,
        params={"role": "student"},
        json={
            "name": "Metformin",
            "dose": "500 mg",
            "route": "by mouth with food",
            "frequency": "twice daily",
            "adherence": "misses evening doses",
            "accessCost": "copay is hard to afford",
        },
    )
    assert medication.status_code == 200, medication.text
    row = next(item for item in medication.json()["medications"] if item["name"] == "Metformin")
    assert row["route"] == "by mouth with food"
    assert row["frequency"] == "twice daily"
    assert row["adherence"] == "misses evening doses"
    assert row["accessCost"] == "copay is hard to afford"

    roomed = await client.patch(
        f"/api/v1/patients/{chart['id']}/status",
        headers=student,
        params={"role": "student"},
        json={"encounter": "Roomed"},
    )
    assert roomed.status_code == 200, roomed.text
    assert roomed.json()["status"]["encounter"] == "Roomed"
