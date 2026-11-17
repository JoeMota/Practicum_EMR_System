"""Simulation handoff: private grading stays private, a shared chart changes hands."""

import pytest

from tests.test_workflows import course_id, login, patient_by_mrn

NURSE = "daniel.reyes@miners.utep.edu"
PHARMACIST = "clarissa.dominguez@miners.utep.edu"
PROVIDER = "ana.rios@miners.utep.edu"
OUTSIDER = "sam.torres@miners.utep.edu"
INSTRUCTOR = "gerardo.sillas@utep.edu"


async def _ids(client, headers, course: str) -> dict[str, str]:
    roster = await client.get(f"/api/v1/courses/{course}/roster", headers=headers)
    assert roster.status_code == 200, roster.text
    return {row["email"]: row["id"] for row in roster.json()}


async def _start(client):
    instructor, _ = await login(client, INSTRUCTOR)
    nurse, _ = await login(client, NURSE)
    pharmacist, _ = await login(client, PHARMACIST)
    provider, _ = await login(client, PROVIDER)
    outsider, _ = await login(client, OUTSIDER)
    course = await course_id(client, instructor, "PHAR 5320")
    people = await _ids(client, instructor, course)
    cases = await client.get("/api/v1/cases", headers=instructor, params={"course_id": course, "role": "instructor"})
    assert cases.status_code == 200, cases.text
    assert cases.json(), "seed should include a case master"
    started = await client.post(
        f"/api/v1/cases/{cases.json()[0]['id']}/simulations",
        headers=instructor,
        params={"course_id": course, "role": "instructor"},
        json={
            "nurseId": people[NURSE],
            "pharmacistId": people[PHARMACIST],
            "providerId": people[PROVIDER],
        },
    )
    assert started.status_code == 200, started.text
    chart = started.json()
    assert chart["mode"] == "simulation"
    assert chart["simulationPhase"] == "waiting_vitals"
    assert chart["vitals"] == []
    return {
        "course": course,
        "chart": chart,
        "instructor": instructor,
        "nurse": nurse,
        "pharmacist": pharmacist,
        "provider": provider,
        "outsider": outsider,
        "people": people,
    }


@pytest.mark.asyncio
async def test_simulation_handoff_closes_note_and_keeps_assessment_private(client):
    sim = await _start(client)
    chart_id = sim["chart"]["id"]

    hidden = await client.get(f"/api/v1/patients/{chart_id}", headers=sim["outsider"], params={"role": "student"})
    assert hidden.status_code == 403

    course = sim["course"]
    sam = await patient_by_mrn(client, sim["instructor"], course, "instructor", "TR-10057-ST")
    still_private = await client.get(f"/api/v1/patients/{sam['id']}", headers=sim["nurse"], params={"role": "student"})
    assert still_private.status_code == 403

    blocked = await client.post(
        f"/api/v1/patients/{chart_id}/vitals",
        headers=sim["pharmacist"],
        params={"role": "student"},
        json={"label": "BP", "value": "118/76 mmHg"},
    )
    assert blocked.status_code == 403

    early = await client.post(
        f"/api/v1/patients/{chart_id}/notes",
        headers=sim["pharmacist"],
        params={"role": "student"},
        json={"templateId": "pharmacy_mtm", "discipline": "pharmacy", "kind": "clarification"},
    )
    assert early.status_code == 409

    recorded = await client.post(
        f"/api/v1/patients/{chart_id}/vitals",
        headers=sim["nurse"],
        params={"role": "student"},
        json={"label": "BP", "value": "128/82 mmHg"},
    )
    assert recorded.status_code == 200, recorded.text
    assert recorded.json()["simulationPhase"] == "ready"

    nurse_note = await client.post(
        f"/api/v1/patients/{chart_id}/notes",
        headers=sim["nurse"],
        params={"role": "student"},
        json={"templateId": "pharmacy_mtm", "discipline": "pharmacy"},
    )
    assert nurse_note.status_code == 403

    created = await client.post(
        f"/api/v1/patients/{chart_id}/notes",
        headers=sim["pharmacist"],
        params={"role": "student"},
        json={"templateId": "pharmacy_mtm", "discipline": "pharmacy"},
    )
    assert created.status_code == 200, created.text
    note_id = created.json()["id"]
    assert created.json()["kind"] == "visit"

    shared = await client.get(
        f"/api/v1/patients/{chart_id}/notes", headers=sim["provider"], params={"role": "student"},
    )
    assert shared.status_code == 200
    assert any(row["id"] == note_id for row in shared.json())

    edited = await client.patch(
        f"/api/v1/notes/{note_id}",
        headers=sim["provider"],
        params={"role": "student"},
        json={"expectedVersion": created.json()["version"], "content": {"reason": "Blood pressure follow-up"}},
    )
    assert edited.status_code == 200, edited.text

    signed = await client.post(
        f"/api/v1/notes/{note_id}/sign",
        headers=sim["provider"],
        params={"role": "student"},
        json={"expectedVersion": edited.json()["version"]},
    )
    assert signed.status_code == 200, signed.text
    assert signed.json()["status"] == "signed"
    assert signed.json()["bodyLocked"] is True

    chart = await client.get(f"/api/v1/patients/{chart_id}", headers=sim["nurse"], params={"role": "student"})
    assert chart.json()["simulationPhase"] == "closed"

    queue = await client.get(
        "/api/v1/review-queue", headers=sim["instructor"], params={"course_id": course, "role": "instructor"},
    )
    assert queue.status_code == 200
    assert all(row["note"]["id"] != note_id for row in queue.json())

    locked = await client.patch(
        f"/api/v1/notes/{note_id}",
        headers=sim["provider"],
        params={"role": "student"},
        json={"expectedVersion": signed.json()["version"], "content": {"reason": "too late"}},
    )
    assert locked.status_code == 409

    clarification = await client.post(
        f"/api/v1/patients/{chart_id}/notes",
        headers=sim["nurse"],
        params={"role": "student"},
        json={"templateId": "pharmacy_mtm", "discipline": "pharmacy", "kind": "clarification"},
    )
    assert clarification.status_code == 200, clarification.text
    assert clarification.json()["kind"] == "clarification"
    assert clarification.json()["id"] != note_id

    audit = await client.get("/api/v1/audit", headers=sim["instructor"], params={"course_id": course, "role": "instructor"})
    assert audit.status_code == 200
    vital_rows = [row for row in audit.json() if row["action"] == "vital.add" and chart_id in row["entity"]]
    assert vital_rows
    assert vital_rows[0]["actorId"] == sim["people"][NURSE]
