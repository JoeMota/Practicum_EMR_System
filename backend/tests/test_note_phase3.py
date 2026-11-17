"""Phase 3: general SOAP stores a per-problem rationale without rejecting empty sections."""

import pytest

from tests.test_workflows import course_id, login, patient_by_mrn


@pytest.mark.asyncio
async def test_general_soap_saves_structured_history_and_rationale(client):
    student, _ = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, student, "PHAR 5320")
    chart = await patient_by_mrn(client, student, course, "student", "TR-20001")
    created = await client.post(
        f"/api/v1/patients/{chart['id']}/notes",
        headers=student,
        params={"role": "student"},
        json={"templateId": "general_soap", "discipline": "pharmacy"},
    )
    assert created.status_code == 200, created.text
    saved = await client.patch(
        f"/api/v1/notes/{created.json()['id']}",
        headers=student,
        params={"role": "student"},
        json={
            "expectedVersion": created.json()["version"],
            "content": {
                "hpi_mnemonic": "scholar_mac",
                "hpi": "Older free-text history.",
                "cc": "",
                "ros_mode": "focused",
                "problem_plans": "{}",
            },
            "diagnoses": [
                {"code": "E11.9", "label": "Type 2 diabetes mellitus", "rationale": "Home sugars are high."},
                {"code": "I10", "label": "Essential hypertension", "rationale": "Listed second."},
            ],
        },
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["content"]["hpi_mnemonic"] == "scholar_mac"
    assert body["content"]["hpi"] == "Older free-text history."
    assert [item["code"] for item in body["diagnoses"]] == ["E11.9", "I10"]
    assert body["diagnoses"][0]["rationale"] == "Home sugars are high."
    assert body["diagnoses"][1]["rationale"] == "Listed second."
