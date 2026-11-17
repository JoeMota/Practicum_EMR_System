"""Phase 2 cases: assigned charts stay put, rubric, triggers, and course copy."""

import io

import pytest
from docx import Document

from app.services.hidden import assert_no_hidden
from tests.test_sprint3 import DEMO_CASE
from tests.test_workflows import course_id, login

FINDING = "Warfarin doubles the INR"
EXPLANATION = "Planted interaction for the grader only"
SECOND = "Potassium is 6.2"
SECOND_WHY = "Abnormal lab the student should notice"


def _docx(heading: str) -> bytes:
    document = Document()
    document.add_heading(heading, level=1)
    document.add_paragraph("What the grader scores.")
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


async def _create(client, headers, course: str, **extra) -> dict:
    body = dict(DEMO_CASE)
    body.update(extra)
    created = await client.post(
        "/api/v1/cases",
        headers=headers,
        params={"course_id": course, "role": "instructor"},
        json=body,
    )
    assert created.status_code == 200, created.text
    return created.json()


async def _assign(client, headers, course: str, case_id: str, owner_id: str) -> dict:
    assigned = await client.post(
        "/api/v1/patients",
        headers=headers,
        params={"course_id": course, "role": "instructor"},
        json={"sourcePatientId": case_id, "ownerId": owner_id},
    )
    assert assigned.status_code == 200, assigned.text
    return assigned.json()


@pytest.mark.asyncio
async def test_case_emergency_contact_round_trip(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    master = await _create(
        client,
        instructor,
        course,
        emergencyContactName="Rosa Demo Contact",
        emergencyContactPhone="915-555-0102",
        emergencyContactRelationship="Sibling",
    )
    contact = master["emergencyContact"]
    assert contact["name"] == "Rosa Demo Contact"
    assert contact["phone"] == "915-555-0102"
    assert contact["relationship"] == "Sibling"

    edited = dict(DEMO_CASE)
    edited.update(
        emergencyContactName="Jordan Morgan",
        emergencyContactPhone="915-555-0182",
        emergencyContactRelationship="Spouse",
    )
    patched = await client.patch(
        f"/api/v1/cases/{master['id']}",
        headers=instructor,
        params={"role": "instructor"},
        json=edited,
    )
    assert patched.status_code == 200, patched.text
    updated = patched.json()["emergencyContact"]
    assert updated["name"] == "Jordan Morgan"
    assert updated["phone"] == "915-555-0182"
    assert updated["relationship"] == "Spouse"


@pytest.mark.asyncio
async def test_case_lung_sounds_round_trip(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    master = await _create(
        client,
        instructor,
        course,
        lungSounds=[
            {"location": "RUL", "finding": "clear"},
            {"location": "RLL", "finding": "crackles", "notes": "Bases"},
        ],
    )
    sounds = master["lungSounds"]
    assert {row["location"]: row["finding"] for row in sounds} == {"RUL": "clear", "RLL": "crackles"}
    assert next(row for row in sounds if row["location"] == "RLL")["notes"] == "Bases"

    edited = dict(DEMO_CASE)
    edited["lungSounds"] = [{"location": "LLL", "finding": "wheeze"}]
    patched = await client.patch(
        f"/api/v1/cases/{master['id']}",
        headers=instructor,
        params={"role": "instructor"},
        json=edited,
    )
    assert patched.status_code == 200, patched.text
    updated = patched.json()["lungSounds"]
    assert len(updated) == 1
    assert updated[0]["location"] == "LLL"
    assert updated[0]["finding"] == "wheeze"


@pytest.mark.asyncio
async def test_case_code_status_and_hipaa_round_trip(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    master = await _create(
        client,
        instructor,
        course,
        codeStatus="DNR",
        advanceDirectiveNotes="Simulated DNR on file.",
        hipaaOnFile=True,
        hipaaNote="Teaching consent on file.",
    )
    assert master["codeStatus"] == "DNR"
    assert master["advanceDirectiveNotes"] == "Simulated DNR on file."
    assert master["hipaaOnFile"] is True
    assert master["hipaaSignedAt"]
    assert master["hipaaNote"] == "Teaching consent on file."

    edited = dict(DEMO_CASE)
    edited.update(
        codeStatus="Full code",
        advanceDirectiveNotes="",
        hipaaOnFile=False,
        hipaaNote="",
    )
    patched = await client.patch(
        f"/api/v1/cases/{master['id']}",
        headers=instructor,
        params={"role": "instructor"},
        json=edited,
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["codeStatus"] == "Full code"
    assert body["hipaaOnFile"] is False
    assert body.get("hipaaSignedAt") in (None, "")


@pytest.mark.asyncio
async def test_later_lock_edits_do_not_change_assigned_charts(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    _, daniel = await login(client, "daniel.reyes@miners.utep.edu")
    _, ana = await login(client, "ana.rios@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    master = await _create(
        client, instructor, course,
        sectionLocks={"vitals": False},
        prefillSections=["vitals"],
    )
    first = await _assign(client, instructor, course, master["id"], daniel["user"]["id"])

    edited = dict(DEMO_CASE)
    edited["sectionLocks"] = {"vitals": True}
    edited["prefillSections"] = ["labs"]
    patched = await client.patch(
        f"/api/v1/cases/{master['id']}",
        headers=instructor,
        params={"role": "instructor"},
        json=edited,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["sectionLocks"]["vitals"] is True
    assert patched.json()["prefillSections"] == ["labs"]

    kept = await client.get(f"/api/v1/patients/{first['id']}", headers=instructor, params={"role": "instructor"})
    assert kept.status_code == 200, kept.text
    assert kept.json()["sectionLocks"]["vitals"] is False
    assert kept.json()["prefillSections"] == ["vitals"]

    second = await _assign(client, instructor, course, master["id"], ana["user"]["id"])
    assert second["sectionLocks"]["vitals"] is True
    assert second["prefillSections"] == ["labs"]


@pytest.mark.asyncio
async def test_case_rubric_falls_back_to_the_course_and_hides_scores(client):
    instructor, instructor_session = await login(client, "gerardo.sillas@utep.edu")
    student, me = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    course_file = await client.post(
        f"/api/v1/courses/{course}/grading-guide",
        headers=instructor,
        files={"file": ("course.docx", _docx("Course criterion (4 points)"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert course_file.status_code == 200, course_file.text

    plain = await _create(client, instructor, course, lastName="NoRubric")
    plain_chart = await _assign(client, instructor, course, plain["id"], me["user"]["id"])
    fallback = await client.get(
        f"/api/v1/patients/{plain_chart['id']}/grading-guide",
        headers=student,
        params={"role": "student"},
    )
    assert fallback.status_code == 200, fallback.text
    assert fallback.json()["criteria"] == []
    assert fallback.json()["file_name"] is None
    assert "rubricScores" not in fallback.json()

    subjective = await _create(client, instructor, course, lastName="SubjectiveCase")
    plan = await _create(client, instructor, course, lastName="PlanCase")
    for case, name, heading in (
        (subjective, "subjective.docx", "Subjective (4 points)"),
        (plan, "plan.docx", "Plan (5 points)"),
    ):
        uploaded = await client.post(
            f"/api/v1/cases/{case['id']}/rubric",
            headers=instructor,
            params={"role": "instructor"},
            files={"file": (name, _docx(heading), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert uploaded.status_code == 200, uploaded.text

    ana, ana_session = await login(client, "ana.rios@miners.utep.edu")
    left = await _assign(client, instructor, course, subjective["id"], me["user"]["id"])
    right = await _assign(client, instructor, course, plan["id"], ana_session["user"]["id"])
    left_guide = await client.get(
        f"/api/v1/patients/{left['id']}/grading-guide", headers=student, params={"role": "student"},
    )
    right_guide = await client.get(
        f"/api/v1/patients/{right['id']}/grading-guide", headers=ana, params={"role": "student"},
    )
    assert left_guide.json()["criteria"] == []
    assert right_guide.json()["criteria"] == []
    staff_guide = await client.get(
        f"/api/v1/patients/{left['id']}/grading-guide", headers=instructor, params={"role": "instructor"},
    )
    assert staff_guide.json()["source"] == "case"
    assert [item["label"] for item in staff_guide.json()["criteria"]] == ["Subjective"]
    assert_no_hidden(left_guide.json())

    created = await client.post(
        f"/api/v1/patients/{left['id']}/notes",
        headers=student,
        params={"role": "student"},
        json={"templateId": "pharmacy_soap", "discipline": "pharmacy"},
    )
    assert created.status_code == 200, created.text
    note_id = created.json()["id"]
    routed = await client.patch(
        f"/api/v1/notes/{note_id}",
        headers=student,
        params={"role": "student"},
        json={"expectedVersion": created.json()["version"], "routedToId": instructor_session["user"]["id"]},
    )
    signed = await client.post(
        f"/api/v1/notes/{note_id}/sign",
        headers=student,
        params={"role": "student"},
        json={"expectedVersion": routed.json()["version"]},
    )
    assert signed.status_code == 200, signed.text
    scored = await client.put(
        f"/api/v1/notes/{note_id}/scores",
        headers=instructor,
        params={"role": "instructor"},
        json={"criteria": [{"id": "c1", "score": 3, "feedback": "Hidden score note", "maxPoints": 4}], "overallFeedback": "Secret overall"},
    )
    assert scored.status_code == 200, scored.text
    student_note = await client.get(f"/api/v1/notes/{note_id}", headers=student, params={"role": "student"})
    assert student_note.status_code == 200, student_note.text
    assert "rubricScores" not in student_note.json()
    assert "Hidden score note" not in str(student_note.json())
    assert "Secret overall" not in str(student_note.json())
    staff_note = await client.get(f"/api/v1/notes/{note_id}", headers=instructor, params={"role": "instructor"})
    assert staff_note.json()["rubricScores"]["overall_feedback"] == "Secret overall"


@pytest.mark.asyncio
async def test_planted_triggers_reach_the_reviewer_and_not_the_student(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    student, me = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    master = await _create(client, instructor, course, lastName="Triggered")
    saved = await client.put(
        f"/api/v1/cases/{master['id']}/triggers",
        headers=instructor,
        params={"role": "instructor"},
        json={"triggers": [
            {"finding": FINDING, "explanation": EXPLANATION},
            {"finding": "  ", "explanation": "drop me"},
            {"finding": SECOND, "explanation": SECOND_WHY},
        ]},
    )
    assert saved.status_code == 200, saved.text
    assert [item["finding"] for item in saved.json()["triggers"]] == [FINDING, SECOND]

    chart = await _assign(client, instructor, course, master["id"], me["user"]["id"])
    note = await client.post(
        f"/api/v1/patients/{chart['id']}/notes",
        headers=student,
        params={"role": "student"},
        json={"templateId": "pharmacy_soap", "discipline": "pharmacy"},
    )
    assert note.status_code == 200, note.text

    reads = [
        await client.get(f"/api/v1/cases/{master['id']}", headers=student, params={"role": "student"}),
        await client.get(f"/api/v1/patients/{chart['id']}", headers=student, params={"role": "student"}),
        await client.get(f"/api/v1/notes/{note.json()['id']}", headers=student, params={"role": "student"}),
        await client.get(f"/api/v1/patients/{chart['id']}/triggers", headers=student, params={"role": "student"}),
    ]
    assert reads[0].status_code == 403
    assert reads[3].status_code == 403
    for response in reads:
        text = str(response.json())
        assert FINDING not in text
        assert EXPLANATION not in text
        assert SECOND not in text
        if response.status_code == 200:
            assert_no_hidden(response.json())

    review = await client.get(
        f"/api/v1/patients/{chart['id']}/triggers",
        headers=instructor,
        params={"role": "instructor"},
    )
    assert review.status_code == 200, review.text
    assert review.json()["triggers"][0]["finding"] == FINDING
    assert review.json()["triggers"][0]["explanation"] == EXPLANATION
    assert review.json()["triggers"][1]["explanation"] == SECOND_WHY


@pytest.mark.asyncio
async def test_copy_case_into_another_course(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    joe, _ = await login(client, "joe.mota@utep.edu")
    _, daniel = await login(client, "daniel.reyes@miners.utep.edu")
    pharmacy = await course_id(client, instructor, "PHAR 5320")
    therapy = await course_id(client, instructor, "PHYT 6310")
    master = await _create(client, instructor, course=pharmacy, chiefComplaint="Copied complaint", lastName="Portable")
    await _assign(client, instructor, pharmacy, master["id"], daniel["user"]["id"])
    await client.put(
        f"/api/v1/cases/{master['id']}/answer-key",
        headers=instructor,
        params={"role": "instructor"},
        json={"diagnoses": [{"code": "I10", "label": "Essential hypertension", "rationale": "Lead problem."}], "planPoints": ["Recheck pressure"], "rationale": "Shared key."},
    )
    await client.put(
        f"/api/v1/cases/{master['id']}/triggers",
        headers=instructor,
        params={"role": "instructor"},
        json={"triggers": [{"finding": FINDING, "explanation": EXPLANATION}]},
    )
    uploaded = await client.post(
        f"/api/v1/cases/{master['id']}/rubric",
        headers=instructor,
        params={"role": "instructor"},
        files={"file": ("copy.docx", _docx("Copied criterion (3 points)"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert uploaded.status_code == 200, uploaded.text

    denied = await client.post(
        f"/api/v1/cases/{master['id']}/copy",
        headers=joe,
        params={"role": "instructor"},
        json={"courseId": therapy},
    )
    assert denied.status_code == 403

    copied = await client.post(
        f"/api/v1/cases/{master['id']}/copy",
        headers=instructor,
        params={"role": "instructor"},
        json={"courseId": therapy},
    )
    assert copied.status_code == 200, copied.text
    clone = copied.json()
    assert clone["id"] != master["id"]
    assert clone["caseTemplateId"] != master["caseTemplateId"]
    assert clone["chiefComplaint"] == "Copied complaint"
    assert clone.get("ownerId") is None
    assert clone["triggers"][0]["finding"] == FINDING
    assert clone["gradingGuide"]["criteria"][0]["label"] == "Copied criterion"

    key = await client.get(f"/api/v1/cases/{clone['id']}/answer-key", headers=instructor, params={"role": "instructor"})
    assert key.status_code == 200, key.text
    assert key.json()["diagnoses"][0]["code"] == "I10"
    assert key.json()["rationale"] == "Shared key."

    roster = await client.get("/api/v1/patients", headers=instructor, params={"course_id": therapy, "role": "instructor"})
    assert all(row["patient"]["caseTemplateId"] != clone["caseTemplateId"] for row in roster.json())

    changed = dict(DEMO_CASE)
    changed["lastName"] = "Portable"
    changed["chiefComplaint"] = "Only the source changed"
    patched = await client.patch(
        f"/api/v1/cases/{master['id']}",
        headers=instructor,
        params={"role": "instructor"},
        json=changed,
    )
    assert patched.status_code == 200, patched.text
    again = await client.get(f"/api/v1/cases/{clone['id']}", headers=instructor, params={"role": "instructor"})
    assert again.json()["chiefComplaint"] == "Copied complaint"
