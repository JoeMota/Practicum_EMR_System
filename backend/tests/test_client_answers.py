import io

import pytest
from docx import Document
from openpyxl import load_workbook

from app.services.case_import import template_workbook
from app.clinical_sections import DELETED_CPT_CODES
from app.services.reference_data import lexicomp_status, search_cpt
from app.services.rubric_import import guide_from_upload
from tests.test_workflows import course_id, login, patient_by_mrn


def test_cpt_list_has_no_prices_and_includes_office_codes():
    codes = {row["code"] for row in search_cpt("")}
    assert {"99211", "99212", "99213", "99214", "99215"} <= codes
    for row in search_cpt("99213"):
        assert set(row) == {"code", "label"}
    assert not ({row["code"] for row in search_cpt("")} & set(DELETED_CPT_CODES))


def test_lexicomp_is_unconfigured_without_a_url(monkeypatch):
    monkeypatch.setattr("app.services.reference_data.settings.LEXICOMP_URL", None)
    monkeypatch.setattr("app.services.reference_data.settings.LEXICOMP_API_URL", None)
    monkeypatch.setattr("app.services.reference_data.settings.LEXICOMP_API_KEY", None)
    status = lexicomp_status()
    assert status["configured"] is False
    assert status["url"] is None
    assert status["detail"] == "The interaction check is unavailable."


def test_word_rubric_becomes_criteria():
    document = Document()
    document.add_heading("Subjective (4 points)", level=1)
    document.add_paragraph("Chief concern and medication experience.")
    document.add_heading("Plan (4 points)", level=1)
    document.add_paragraph("Numbered recommendations and follow-up.")
    buffer = io.BytesIO()
    document.save(buffer)
    guide = guide_from_upload("SOAP.docx", buffer.getvalue())
    assert [item["label"] for item in guide["criteria"]] == ["Subjective", "Plan"]
    assert guide["criteria"][0]["max_points"] == 4


def test_case_template_headers_match_the_importer():
    book = load_workbook(io.BytesIO(template_workbook()))
    headers = [cell.value for cell in next(book["Cases"].iter_rows(max_row=1))]
    assert headers[0] == "first_name"
    assert "allergies" in headers
    assert headers[-3:] == ["unit", "room", "bed"]


@pytest.mark.asyncio
async def test_student_archives_a_medication_and_cannot_edit_locked_diagnoses(client):
    student, _ = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, student, "PHAR 5320")
    chart = await patient_by_mrn(client, student, course, "student", "TR-20001")
    medication_id = chart["medications"][0]["id"]

    archived = await client.post(
        f"/api/v1/patients/{chart['id']}/medications/{medication_id}/discontinue",
        headers=student,
        params={"role": "student"},
    )
    assert archived.status_code == 200, archived.text
    updated = next(item for item in archived.json()["medications"] if item["id"] == medication_id)
    assert updated["status"] == "discontinued"

    removed = await client.delete(
        f"/api/v1/patients/{chart['id']}/medications/{medication_id}",
        headers=student,
        params={"role": "student"},
    )
    assert removed.status_code == 409

    mistake = await client.delete(
        f"/api/v1/patients/{chart['id']}/medications/{medication_id}",
        headers=student,
        params={"role": "student", "reason": "entered_in_error"},
    )
    assert mistake.status_code == 200, mistake.text
    assert all(item["id"] != medication_id for item in mistake.json()["medications"])

    blocked = await client.post(
        f"/api/v1/patients/{chart['id']}/problems",
        headers=student,
        params={"role": "student"},
        json={"description": "Student-added diagnosis", "code": "I10"},
    )
    assert blocked.status_code == 403


@pytest.mark.asyncio
async def test_instructor_cannot_enroll_students(client):
    instructor, _ = await login(client, "joe.mota@utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    response = await client.post(
        f"/api/v1/courses/{course}/roster/import",
        headers=instructor,
        json={
            "discipline": "pharmacy",
            "role": "student",
            "rows": [{"fullName": "New Student", "email": "new.student2@miners.utep.edu", "universityId": "800888888"}],
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_addendum_reopens_a_signed_note_for_grading(client):
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
    created = await client.post(
        f"/api/v1/patients/{assigned.json()['id']}/notes",
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
    cosigned = await client.post(
        f"/api/v1/notes/{note_id}/cosign",
        headers=instructor,
        params={"role": "instructor"},
        json={"comment": "Accepted."},
    )
    assert cosigned.json()["bodyLocked"] is True
    edited = await client.patch(
        f"/api/v1/notes/{note_id}",
        headers=student,
        params={"role": "student"},
        json={"expectedVersion": cosigned.json()["version"], "content": {"subjective": "Changed after signature"}},
    )
    assert edited.status_code == 409
    addendum = await client.post(
        f"/api/v1/notes/{note_id}/addenda",
        headers=student,
        params={"role": "student"},
        json={"body": "Corrected the follow-up interval."},
    )
    assert addendum.status_code == 200, addendum.text
    assert addendum.json()["status"] == "pending_review"
    assert addendum.json()["addenda"][0]["body"] == "Corrected the follow-up interval."


@pytest.mark.asyncio
async def test_admin_enrolls_existing_people_and_resets_a_password(client):
    admin, session = await login(client, "clarissa.dominguez@utep.edu")
    course = await course_id(client, admin, "PHYT 6310")
    found = await client.get("/api/v1/users", headers=admin, params={"q": "Joe Mota"})
    assert found.status_code == 200, found.text
    joe = next(person for person in found.json() if person["email"] == "joe.mota@utep.edu")
    daniel = next(
        person for person in (await client.get("/api/v1/users", headers=admin, params={"q": "daniel.reyes"})).json()
        if person["email"] == "daniel.reyes@miners.utep.edu"
    )

    instructor_seat = await client.post(
        f"/api/v1/courses/{course}/enrollments",
        headers=admin,
        json={"userId": joe["id"], "role": "instructor", "discipline": "physical_therapy"},
    )
    assert instructor_seat.status_code == 200, instructor_seat.text
    student_seat = await client.post(
        f"/api/v1/courses/{course}/enrollments",
        headers=admin,
        json={"userId": daniel["id"], "role": "student", "discipline": "physical_therapy"},
    )
    assert student_seat.status_code == 200, student_seat.text
    duplicate = await client.post(
        f"/api/v1/courses/{course}/enrollments",
        headers=admin,
        json={"userId": joe["id"], "role": "instructor", "discipline": "physical_therapy"},
    )
    assert duplicate.status_code == 409

    created = await client.post(
        f"/api/v1/courses/{course}/roster/import",
        headers=admin,
        json={
            "discipline": "physical_therapy",
            "role": "instructor",
            "rows": [{"fullName": "New Instructor", "email": "new.instructor@utep.edu", "universityId": ""}],
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["added"] == 1
    assert created.json()["temporaryPasswords"][0]["email"] == "new.instructor@utep.edu"
    created_account = next(
        person for person in (await client.get("/api/v1/users", headers=admin, params={"q": "new.instructor"})).json()
        if person["email"] == "new.instructor@utep.edu"
    )
    reset = await client.post(f"/api/v1/users/{created_account['id']}/reset-password", headers=admin)
    assert reset.status_code == 200, reset.text
    assert reset.json()["email"] == "new.instructor@utep.edu"
    assert reset.json()["password"]
    own = await client.post(f"/api/v1/users/{session['user']['id']}/reset-password", headers=admin)
    assert own.status_code == 409

    instructor, _ = await login(client, "joe.mota@utep.edu")
    hidden = await client.get("/api/v1/users", headers=instructor, params={"q": "Daniel"})
    assert hidden.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_edit_an_account_and_coordinators_stay_with_the_admin(client):
    admin, _ = await login(client, "clarissa.dominguez@utep.edu")
    course = await course_id(client, admin, "PHAR 5320")
    daniel = next(
        person for person in (await client.get("/api/v1/users", headers=admin, params={"q": "daniel.reyes"})).json()
        if person["email"] == "daniel.reyes@miners.utep.edu"
    )
    edited = await client.patch(
        f"/api/v1/users/{daniel['id']}",
        headers=admin,
        json={"fullName": "Daniel R Reyes", "email": daniel["email"], "universityId": "800123456"},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["fullName"] == "Daniel R Reyes"

    instructor, _ = await login(client, "joe.mota@utep.edu")
    denied = await client.patch(
        f"/api/v1/users/{daniel['id']}",
        headers=instructor,
        json={"fullName": "Daniel Reyes", "email": daniel["email"], "universityId": "800123456"},
    )
    assert denied.status_code == 403

    joe = next(
        person for person in (await client.get("/api/v1/users", headers=admin, params={"q": "joe.mota"})).json()
        if person["email"] == "joe.mota@utep.edu"
    )
    seated = await client.post(
        f"/api/v1/courses/{course}/enrollments",
        headers=admin,
        json={"userId": joe["id"], "role": "course_coordinator", "discipline": "pharmacy"},
    )
    assert seated.status_code == 200, seated.text
    removed = await client.delete(
        f"/api/v1/courses/{course}/roster/{joe['id']}",
        headers=instructor,
        params={"role": "course_coordinator"},
    )
    assert removed.status_code == 403


@pytest.mark.asyncio
async def test_admin_activity_log_is_available_without_a_course(client):
    admin, _ = await login(client, "clarissa.dominguez@utep.edu")
    everything = await client.get("/api/v1/audit", headers=admin, params={"role": "admin"})
    assert everything.status_code == 200, everything.text
    assert isinstance(everything.json(), list)

    course = await course_id(client, admin, "PHAR 5320")
    one_class = await client.get("/api/v1/audit", headers=admin, params={"role": "admin", "course_id": course})
    assert one_class.status_code == 200, one_class.text

    instructor, _ = await login(client, "joe.mota@utep.edu")
    missing_course = await client.get("/api/v1/audit", headers=instructor, params={"role": "instructor"})
    assert missing_course.status_code == 422
