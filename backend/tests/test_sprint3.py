"""Sprint 3: case masters stay hidden, and answer keys never reach a student."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app.models.audit import AuditEvent
from app.models.clinical import CaseAnswerKey, Patient
from app.services.hidden import assert_no_hidden
from tests.test_workflows import course_id, login

DEMO_CASE = {
    "firstName": "Nora",
    "lastName": "Iqbal",
    "dob": "1974-06-19",
    "sexAtBirth": "Female",
    "chiefComplaint": "Blood pressure follow-up",
    "hpi": "Here for a medication check.",
    "pastMedicalHistory": "Hypertension.",
    "surgicalHistory": "None.",
    "familyHistory": "Mother with diabetes.",
    "socialHistory": "No tobacco.",
    "encounterType": "Office visit",
    "careSetting": "Outpatient",
    "lifecycle": "Active",
    "encounterStatus": "Scheduled",
    "program": "Pharmacy",
    "medications": [
        {"name": "Lisinopril", "dose": "10 mg", "route": "PO", "frequency": "daily"},
    ],
}


def _as_case_body(case: dict) -> dict:
    status = case["status"]
    return {
        "firstName": case["firstName"],
        "lastName": case["lastName"],
        "preferredName": case.get("preferredName"),
        "dob": case["dob"],
        "sexAtBirth": case["sexAtBirth"],
        "pronouns": case.get("pronouns"),
        "chiefComplaint": case["chiefComplaint"],
        "hpi": case["hpi"],
        "pastMedicalHistory": case.get("pastMedicalHistory") or "",
        "surgicalHistory": case["surgicalHistory"],
        "familyHistory": case["familyHistory"],
        "socialHistory": case["socialHistory"],
        "encounterType": case["encounter"]["type"],
        "careSetting": status["careSetting"],
        "lifecycle": status["lifecycle"],
        "encounterStatus": status["encounter"],
        "program": status.get("program"),
        "allergies": case["allergies"],
        "medications": [
            {
                "name": med["name"],
                "dose": med["dose"],
                "route": med["route"],
                "frequency": med["frequency"],
                "indication": med.get("indication"),
                "adherence": med.get("adherence"),
            }
            for med in case["medications"]
        ],
        "problems": case["problems"],
        "labs": [
            {
                "name": lab["name"],
                "value": lab["value"],
                "unit": lab["unit"],
                "referenceRange": lab["referenceRange"],
                "flag": lab.get("flag"),
                "collectedAt": lab["collectedAt"],
            }
            for lab in case["labs"]
        ],
        "vitals": [{"label": vital["label"], "value": vital["value"]} for vital in case["vitals"]],
    }


@pytest.mark.asyncio
async def test_instructor_creates_case_master_and_student_is_denied(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    student, _ = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")

    denied = await client.post(
        "/api/v1/cases",
        headers=student,
        params={"course_id": course, "role": "student"},
        json=DEMO_CASE,
    )
    assert denied.status_code == 403

    created = await client.post(
        "/api/v1/cases",
        headers=instructor,
        params={"course_id": course, "role": "instructor"},
        json=DEMO_CASE,
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["mode"] == "case"
    assert body.get("ownerId") is None
    assert body["mrn"].startswith("CASE-")
    assert body["pastMedicalHistory"] == "Hypertension."

    audit = await client.get("/api/v1/audit", headers=instructor, params={"course_id": course, "role": "instructor"})
    assert audit.status_code == 200
    denied_rows = [row for row in audit.json() if row["action"] == "case.create" and row["result"] == "denied"]
    assert denied_rows


@pytest.mark.asyncio
async def test_students_cannot_list_or_open_case_masters(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    student, _ = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    masters = await client.get("/api/v1/cases", headers=instructor, params={"course_id": course, "role": "instructor"})
    assert masters.status_code == 200, masters.text
    master = next(row for row in masters.json() if row["mrn"] == "CASE-10001")

    hidden = await client.get("/api/v1/cases", headers=student, params={"course_id": course, "role": "student"})
    assert hidden.status_code == 403

    for role, headers in (("student", student), ("instructor", instructor)):
        listed = await client.get("/api/v1/patients", headers=headers, params={"course_id": course, "role": role})
        assert listed.status_code == 200
        assert all(row["patient"]["mode"] != "case" for row in listed.json())
        assert master["id"] not in {row["patient"]["id"] for row in listed.json()}

    opened = await client.get(f"/api/v1/patients/{master['id']}", headers=student, params={"role": "student"})
    assert opened.status_code == 403


@pytest.mark.asyncio
async def test_editing_master_leaves_assigned_copy_and_snapshot_unchanged(client, db_session):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    student, me = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    masters = await client.get("/api/v1/cases", headers=instructor, params={"course_id": course, "role": "instructor"})
    master = next(row for row in masters.json() if row["mrn"] == "CASE-10001")
    original_complaint = master["chiefComplaint"]
    original_med = master["medications"][0]["name"]

    assigned = await client.post(
        "/api/v1/patients",
        headers=instructor,
        params={"course_id": course, "role": "instructor"},
        json={"sourcePatientId": master["id"], "ownerId": me["user"]["id"]},
    )
    assert assigned.status_code == 200, assigned.text
    copy = assigned.json()
    assert copy["chiefComplaint"] == original_complaint
    assert copy["mode"] == "assessment"

    edited = _as_case_body(master)
    edited["chiefComplaint"] = "Edited after assignment"
    edited["medications"][0]["name"] = "Enalapril"
    patched = await client.patch(
        f"/api/v1/cases/{master['id']}",
        headers=instructor,
        params={"role": "instructor"},
        json=edited,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["chiefComplaint"] == "Edited after assignment"

    reread = await client.get(f"/api/v1/patients/{copy['id']}", headers=student, params={"role": "student"})
    assert reread.status_code == 200, reread.text
    assert reread.json()["chiefComplaint"] == original_complaint
    assert reread.json()["medications"][0]["name"] == original_med

    stored = await db_session.get(Patient, uuid.UUID(copy["id"]))
    await db_session.refresh(stored)
    assert stored.snapshot["chief_complaint"] == original_complaint
    assert stored.snapshot["medications"][0]["name"] == original_med
    assert stored.chief_complaint == original_complaint


@pytest.mark.asyncio
async def test_seed_creates_one_master_per_case(client):
    from app.scripts.seed import seed

    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    pharmacy = await course_id(client, instructor, "PHAR 5320")
    therapy = await course_id(client, instructor, "PHYT 6310")

    async def mrns(course: str) -> list[str]:
        response = await client.get(
            "/api/v1/cases", headers=instructor, params={"course_id": course, "role": "instructor"}
        )
        assert response.status_code == 200, response.text
        return [row["mrn"] for row in response.json()]

    assert (await mrns(pharmacy)).count("CASE-10001") == 1
    assert (await mrns(therapy)).count("CASE-10002") == 1

    await seed(None, None)

    assert (await mrns(pharmacy)).count("CASE-10001") == 1
    assert (await mrns(therapy)).count("CASE-10002") == 1
    count = await client.get("/api/v1/cases", headers=instructor, params={"course_id": pharmacy, "role": "instructor"})
    assert sum(1 for row in count.json() if row["mrn"] == "CASE-10001") == 1


@pytest.mark.asyncio
async def test_case_list_denial_is_audited(client, db_session):
    student, _ = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, student, "PHAR 5320")
    denied = await client.get("/api/v1/cases", headers=student, params={"course_id": course, "role": "student"})
    assert denied.status_code == 403
    rows = (
        await db_session.scalars(
            select(AuditEvent).where(
                AuditEvent.course_id == uuid.UUID(course),
                AuditEvent.action == "case.list",
                AuditEvent.result == "denied",
            )
        )
    ).all()
    assert rows


def test_hidden_walk_finds_nested_keys():
    with pytest.raises(AssertionError):
        assert_no_hidden({"chart": [{"planPoints": ["secret"]}]})
    assert_no_hidden({"diagnoses": [{"code": "I10", "label": "Essential hypertension"}]})


@pytest.mark.asyncio
async def test_answer_key_replaces_and_stays_hidden(client, db_session):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    student, me = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    created = await client.post(
        "/api/v1/cases",
        headers=instructor,
        params={"course_id": course, "role": "instructor"},
        json=DEMO_CASE,
    )
    assert created.status_code == 200, created.text
    master_id = created.json()["id"]

    denied = await client.put(
        f"/api/v1/cases/{master_id}/answer-key",
        headers=student,
        params={"role": "student"},
        json={"diagnoses": [{"code": "I10", "label": "Essential hypertension"}], "planPoints": ["Secret"], "rationale": "Hidden."},
    )
    assert denied.status_code == 403

    first = {
        "diagnoses": [
            {"rank": 9, "code": "I10", "label": "Essential hypertension", "rationale": "Listed first."},
            {"rank": 1, "code": "E11.9", "label": "Type 2 diabetes mellitus without complications", "rationale": "Listed second."},
        ],
        "expectedCptCodes": [{"code": "99213", "label": "Office visit, established patient, level 3"}],
        "planPoints": ["Confirm home readings", ""],
        "rationale": "Blood pressure is the lead problem.",
    }
    saved = await client.put(
        f"/api/v1/cases/{master_id}/answer-key",
        headers=instructor,
        params={"role": "instructor"},
        json=first,
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert [item["rank"] for item in body["diagnoses"]] == [1, 2]
    assert body["diagnoses"][0]["code"] == "I10"
    assert body["expectedCptCodes"] == [{"code": "99213", "label": "Office visit, established patient, level 3"}]
    assert body["planPoints"] == ["Confirm home readings"]

    replaced = await client.put(
        f"/api/v1/cases/{master_id}/answer-key",
        headers=instructor,
        params={"role": "instructor"},
        json={
            "diagnoses": [{"code": "I10", "label": "Essential hypertension", "rationale": "Only this one."}],
            "expectedCptCodes": first["expectedCptCodes"],
            "planPoints": ["Recheck in four weeks"],
            "rationale": "Replaced.",
        },
    )
    assert replaced.status_code == 200, replaced.text
    assert len(replaced.json()["diagnoses"]) == 1
    assert replaced.json()["rationale"] == "Replaced."

    assigned = await client.post(
        "/api/v1/patients",
        headers=instructor,
        params={"course_id": course, "role": "instructor"},
        json={"sourcePatientId": master_id, "ownerId": me["user"]["id"]},
    )
    assert assigned.status_code == 200, assigned.text
    copy_id = assigned.json()["id"]

    # Release alone is not enough — student still needs a cosigned note (CASE-05 / REV-07).
    stored = await db_session.get(Patient, uuid.UUID(copy_id))
    stored.answer_key_released_at = datetime.now(timezone.utc)
    await db_session.commit()

    student_key = await client.get(f"/api/v1/patients/{copy_id}/answer-key", headers=student, params={"role": "student"})
    assert student_key.status_code == 403
    assert_no_hidden(student_key.json())
    denied_rows = (
        await db_session.scalars(
            select(AuditEvent).where(
                AuditEvent.entity_id == copy_id,
                AuditEvent.action == "answer_key.view",
                AuditEvent.result == "denied",
            )
        )
    ).all()
    assert denied_rows

    instructor_key = await client.get(f"/api/v1/patients/{copy_id}/answer-key", headers=instructor, params={"role": "instructor"})
    assert instructor_key.status_code == 200, instructor_key.text
    assert instructor_key.json()["diagnoses"][0]["code"] == "I10"
    assert instructor_key.json()["expectedCptCodes"] == body["expectedCptCodes"]
    admin, _ = await login(client, "gerardo.sillas@utep.edu", role="admin")
    admin_key = await client.get(f"/api/v1/cases/{master_id}/answer-key", headers=admin, params={"role": "admin"})
    assert admin_key.status_code == 200, admin_key.text
    assert [item["rank"] for item in admin_key.json()["diagnoses"]] == [1]

    note = await client.post(
        f"/api/v1/patients/{copy_id}/notes",
        headers=student,
        params={"role": "student"},
        json={"templateId": "pharmacy_mtm", "discipline": "pharmacy"},
    )
    assert note.status_code == 200, note.text
    note_id = note.json()["id"]

    reads = [
        await client.get("/api/v1/patients", headers=student, params={"course_id": course, "role": "student"}),
        await client.get(f"/api/v1/patients/{copy_id}", headers=student, params={"role": "student"}),
        await client.get(f"/api/v1/patients/{copy_id}/notes", headers=student, params={"role": "student"}),
        await client.get(f"/api/v1/notes/{note_id}", headers=student, params={"role": "student"}),
        await client.get(f"/api/v1/patients/{copy_id}/appointments", headers=student, params={"role": "student"}),
        await client.get(f"/api/v1/patients/{copy_id}/referrals", headers=student, params={"role": "student"}),
        await client.get("/api/v1/auth/me", headers=student),
    ]
    for response in reads:
        assert response.status_code == 200, response.text
        assert_no_hidden(response.json())
    chart = next(item for item in reads if item.request.url.path.endswith(copy_id))
    assert "Replaced." not in response_text(chart.json())


def response_text(payload) -> str:
    return str(payload)


@pytest.mark.asyncio
async def test_seeded_answer_keys_are_not_duplicated(client, db_session):
    from app.scripts.seed import seed

    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    pharmacy = await course_id(client, instructor, "PHAR 5320")
    masters = await client.get("/api/v1/cases", headers=instructor, params={"course_id": pharmacy, "role": "instructor"})
    master = next(row for row in masters.json() if row["mrn"] == "CASE-10001")
    key = await client.get(f"/api/v1/cases/{master['id']}/answer-key", headers=instructor, params={"role": "instructor"})
    assert key.status_code == 200, key.text
    assert [item["code"] for item in key.json()["diagnoses"]] == ["N39.0", "N30.00"]

    await seed(None, None)

    again = await client.get(f"/api/v1/cases/{master['id']}/answer-key", headers=instructor, params={"role": "instructor"})
    assert [item["code"] for item in again.json()["diagnoses"]] == ["N39.0", "N30.00"]
    count = await db_session.scalar(
        select(func.count()).select_from(CaseAnswerKey).where(CaseAnswerKey.patient_id == uuid.UUID(master["id"]))
    )
    assert count == 1


@pytest.mark.asyncio
async def test_section_comment_leaves_the_student_note_unchanged(client, db_session):
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
    assert signed.json()["status"] == "pending_review"
    original = signed.json()["content"]

    denied = await client.post(
        f"/api/v1/notes/{note_id}/comments",
        headers=student,
        params={"role": "student"},
        json={"sectionId": "A", "body": "Students cannot comment."},
    )
    assert denied.status_code == 403

    edited = await client.patch(
        f"/api/v1/notes/{note_id}",
        headers=instructor,
        params={"role": "instructor"},
        json={"expectedVersion": signed.json()["version"], "content": {"reason": "Instructor rewrote this."}},
    )
    assert edited.status_code == 403

    commented = await client.post(
        f"/api/v1/notes/{note_id}/comments",
        headers=instructor,
        params={"role": "instructor"},
        json={"sectionId": "A", "body": "Name the sulfa allergy in the plan."},
    )
    assert commented.status_code == 200, commented.text
    section_comments = [item for item in commented.json()["feedback"] if item["kind"] == "comment"]
    assert section_comments[0]["sectionId"] == "A"
    assert section_comments[0]["body"] == "Name the sulfa allergy in the plan."
    assert_no_hidden(commented.json())

    seen = await client.get(f"/api/v1/notes/{note_id}", headers=student, params={"role": "student"})
    assert seen.status_code == 200, seen.text
    assert seen.json()["content"] == original
    assert any(item["sectionId"] == "A" for item in seen.json()["feedback"])
    assert_no_hidden(seen.json())

    audit = (
        await db_session.scalars(
            select(AuditEvent).where(
                AuditEvent.entity_id == note_id,
                AuditEvent.action == "note.comment",
                AuditEvent.result == "ok",
            )
        )
    ).all()
    assert audit

    cosigned = await client.post(
        f"/api/v1/notes/{note_id}/cosign",
        headers=instructor,
        params={"role": "instructor"},
        json={"comment": "Accepted."},
    )
    assert cosigned.status_code == 200, cosigned.text
    late = await client.post(
        f"/api/v1/notes/{note_id}/comments",
        headers=instructor,
        params={"role": "instructor"},
        json={"sectionId": "P", "body": "Too late."},
    )
    assert late.status_code == 409


@pytest.mark.asyncio
async def test_deactivate_hides_the_course_and_keeps_the_charts(client, db_session):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    student, me = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    student_id = me["user"]["id"]
    before = await client.get("/api/v1/patients", headers=instructor, params={"course_id": course, "role": "instructor"})
    assert before.status_code == 200, before.text
    chart_ids = [row["patient"]["id"] for row in before.json() if row["patient"].get("ownerId") == student_id]
    assert chart_ids

    denied = await client.post(f"/api/v1/courses/{course}/roster/{student_id}/deactivate", headers=student)
    assert denied.status_code == 403
    audit = (
        await db_session.scalars(
            select(AuditEvent).where(
                AuditEvent.course_id == uuid.UUID(course),
                AuditEvent.action == "roster.deactivate",
                AuditEvent.result == "denied",
            )
        )
    ).all()
    assert audit

    deactivated = await client.post(f"/api/v1/courses/{course}/roster/{student_id}/deactivate", headers=instructor)
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["rosterStatus"] == "inactive"

    hidden = await client.get("/api/v1/patients", headers=student, params={"course_id": course, "role": "student"})
    assert hidden.status_code == 403
    profile = await client.get("/api/v1/auth/me", headers=student)
    assert profile.status_code == 200
    assert all(course not in role.get("courseIds", []) for role in profile.json()["roles"])
    still_in = await client.post("/api/v1/auth/login", data={"username": "daniel.reyes@miners.utep.edu", "password": "practicum-demo"})
    assert still_in.status_code == 200

    visible = await client.get("/api/v1/patients", headers=instructor, params={"course_id": course, "role": "instructor"})
    visible_ids = {row["patient"]["id"] for row in visible.json()}
    assert set(chart_ids) <= visible_ids

    masters = await client.get("/api/v1/cases", headers=instructor, params={"course_id": course, "role": "instructor"})
    master = next(row for row in masters.json() if row["mrn"] == "CASE-10001")
    blocked = await client.post(
        "/api/v1/patients",
        headers=instructor,
        params={"course_id": course, "role": "instructor"},
        json={"sourcePatientId": master["id"], "ownerId": student_id},
    )
    assert blocked.status_code == 400

    imported = await client.post(
        f"/api/v1/courses/{course}/roster/import",
        headers=instructor,
        json={
            "discipline": "pharmacy",
            "role": "student",
            "rows": [{"fullName": "Daniel Reyes", "email": "daniel.reyes@miners.utep.edu", "universityId": "800123456"}],
        },
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["reactivated"] == 1
    assert imported.json()["added"] == 0

    restored = await client.get("/api/v1/patients", headers=student, params={"course_id": course, "role": "student"})
    assert restored.status_code == 200, restored.text
    restored_ids = {row["patient"]["id"] for row in restored.json()}
    assert set(chart_ids) <= restored_ids
    opened = await client.get(f"/api/v1/patients/{chart_ids[0]}", headers=student, params={"role": "student"})
    assert opened.status_code == 200, opened.text
