import pytest

DEMO = "practicum-demo"


async def login(client, email: str, password: str = DEMO):
    response = await client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body


async def course_id(client, headers, code: str) -> str:
    response = await client.get("/api/v1/courses", headers=headers)
    assert response.status_code == 200, response.text
    match = next(item for item in response.json() if item["code"] == code)
    return match["id"]


async def patient_by_mrn(client, headers, course: str, role: str, mrn: str) -> dict:
    response = await client.get("/api/v1/patients", headers=headers, params={"course_id": course, "role": role})
    assert response.status_code == 200, response.text
    return next(row["patient"] for row in response.json() if row["patient"]["mrn"] == mrn)


@pytest.mark.asyncio
async def test_login_rejects_non_utep_email(client):
    response = await client.post("/api/v1/auth/login", data={"username": "ada@example.com", "password": "whatever"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_me_returns_frontend_role_shape(client):
    headers, body = await login(client, "daniel.reyes@miners.utep.edu")
    assert body["mustChangePassword"] is False
    roles = body["user"]["roles"]
    assert roles == [{"role": "student", "discipline": "pharmacy", "courseIds": roles[0]["courseIds"]}]
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["fullName"] == "Daniel Reyes"


@pytest.mark.asyncio
async def test_student_cannot_see_another_students_assessment(client):
    headers, _ = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, headers, "PHAR 5320")
    listed = await client.get("/api/v1/patients", headers=headers, params={"course_id": course, "role": "student"})
    mrns = {row["patient"]["mrn"] for row in listed.json()}
    assert "TR-20001" in mrns
    assert "TR-10057-ST" not in mrns

    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    sam = await patient_by_mrn(client, instructor, course, "instructor", "TR-10057-ST")
    denied = await client.get(f"/api/v1/patients/{sam['id']}", headers=headers, params={"role": "student"})
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_admin_course_lifecycle_and_report(client):
    headers, _ = await login(client, "gerardo.sillas@utep.edu")
    created = await client.post(
        "/api/v1/courses",
        headers=headers,
        json={"code": "TEST 1000", "title": "Lifecycle Test", "term": "Fall 2026"},
    )
    assert created.status_code == 201, created.text
    course = created.json()
    assert course["status"] == "planned"

    activated = await client.post(
        f"/api/v1/courses/{course['id']}/status", headers=headers, json={"status": "active"}
    )
    assert activated.status_code == 200
    ended = await client.post(
        f"/api/v1/courses/{course['id']}/status", headers=headers, json={"status": "ended"}
    )
    assert ended.status_code == 200
    roster_blocked = await client.post(
        f"/api/v1/courses/{course['id']}/roster/import",
        headers=headers,
        json={"discipline": "pharmacy", "role": "student", "rows": []},
    )
    assert roster_blocked.status_code == 409
    invalid = await client.post(
        f"/api/v1/courses/{course['id']}/status", headers=headers, json={"status": "planned"}
    )
    assert invalid.status_code == 409
    status_check = await client.get(f"/api/v1/courses/{course['id']}", headers=headers)
    assert status_check.json()["status"] == "ended"

    report = await client.get(f"/api/v1/reports/courses/{course['id']}", headers=headers)
    assert report.status_code == 200
    assert report.json()["studentsEnrolled"] == 0
    assert report.json()["notesByStatus"]["pending_review"] == 0
    csv_report = await client.get(
        f"/api/v1/reports/courses/{course['id']}", headers=headers, params={"format": "csv"}
    )
    assert csv_report.status_code == 200
    assert "text/csv" in csv_report.headers["content-type"]
    assert "students,0" in csv_report.text

    reopened = await client.post(
        f"/api/v1/courses/{course['id']}/status", headers=headers, json={"status": "active"}
    )
    assert reopened.status_code == 200
    ended_again = await client.post(
        f"/api/v1/courses/{course['id']}/status", headers=headers, json={"status": "ended"}
    )
    assert ended_again.status_code == 200
    archived = await client.post(
        f"/api/v1/courses/{course['id']}/status", headers=headers, json={"status": "archived"}
    )
    assert archived.status_code == 200
    archived_blocked = await client.post(
        f"/api/v1/courses/{course['id']}/status", headers=headers, json={"status": "active"}
    )
    assert archived_blocked.status_code == 409
    listed = await client.get("/api/v1/courses", headers=headers)
    assert any(item["id"] == course["id"] and item["status"] == "archived" for item in listed.json())


@pytest.mark.asyncio
async def test_same_course_code_allowed_in_different_terms(client):
    headers, _ = await login(client, "gerardo.sillas@utep.edu")
    first = await client.post(
        "/api/v1/courses",
        headers=headers,
        json={"code": "TEST 4000", "title": "Course A", "term": "Fall 2026"},
    )
    assert first.status_code == 201, first.text

    second = await client.post(
        "/api/v1/courses",
        headers=headers,
        json={"code": "TEST 4000", "title": "Course A", "term": "Spring 2027"},
    )
    assert second.status_code == 201, second.text
    assert second.json()["id"] != first.json()["id"]

    duplicate = await client.post(
        "/api/v1/courses",
        headers=headers,
        json={"code": "TEST 4000", "title": "Course A", "term": "Fall 2026"},
    )
    assert duplicate.status_code == 409
    assert "for that term" in duplicate.json()["detail"]

    listed = await client.get("/api/v1/courses", headers=headers)
    matching_courses = [item for item in listed.json() if item["code"] == "TEST 4000"]
    assert {(item["id"], item["term"]) for item in matching_courses} == {
        (first.json()["id"], "Fall 2026"),
        (second.json()["id"], "Spring 2027"),
    }


@pytest.mark.asyncio
async def test_admin_can_import_single_instructor_and_student(client):
    headers, _ = await login(client, "gerardo.sillas@utep.edu")
    created = await client.post(
        "/api/v1/courses",
        headers=headers,
        json={"code": "TEST 6000", "title": "Single Import", "term": "Fall 2026"},
    )
    assert created.status_code == 201, created.text
    course = await course_id(client, headers, "TEST 6000")

    activated = await client.post(
        f"/api/v1/courses/{course}/status", headers=headers, json={"status": "active"}
    )
    assert activated.status_code == 200, activated.text

    instructor_row = {
        "fullName": "Single Instructor",
        "email": "single.instructor@utep.edu",
        "universityId": "800720001",
    }
    instructor_import = await client.post(
        f"/api/v1/courses/{course}/roster/import",
        headers=headers,
        json={"discipline": "pharmacy", "role": "instructor", "rows": [instructor_row]},
    )
    assert instructor_import.status_code == 200, instructor_import.text
    assert instructor_import.json()["added"] == 1
    assert instructor_import.json()["temporaryPasswords"]
    assert instructor_import.json()["temporaryPasswords"][0]["email"] == instructor_row["email"]

    instructors = await client.get(f"/api/v1/courses/{course}/instructors", headers=headers)
    assert instructors.status_code == 200, instructors.text
    assert sum(person["email"] == instructor_row["email"] for person in instructors.json()) == 1

    duplicate_import = await client.post(
        f"/api/v1/courses/{course}/roster/import",
        headers=headers,
        json={"discipline": "pharmacy", "role": "instructor", "rows": [instructor_row]},
    )
    assert duplicate_import.status_code == 200, duplicate_import.text
    assert duplicate_import.json()["added"] == 0
    assert duplicate_import.json()["alreadyEnrolled"] == 1
    assert duplicate_import.json()["temporaryPasswords"] == []
    instructors = await client.get(f"/api/v1/courses/{course}/instructors", headers=headers)
    assert sum(person["email"] == instructor_row["email"] for person in instructors.json()) == 1

    student_row = {
        "fullName": "Single Student",
        "email": "single.student@miners.utep.edu",
        "universityId": "800720002",
    }
    student_import = await client.post(
        f"/api/v1/courses/{course}/roster/import",
        headers=headers,
        json={"discipline": "pharmacy", "role": "student", "rows": [student_row]},
    )
    assert student_import.status_code == 200, student_import.text
    assert student_import.json()["added"] == 1
    assert student_import.json()["temporaryPasswords"]
    assert student_import.json()["temporaryPasswords"][0]["email"] == student_row["email"]


@pytest.mark.asyncio
async def test_instructor_removal_guards(client):
    admin_headers, _ = await login(client, "gerardo.sillas@utep.edu")
    course = await course_id(client, admin_headers, "PHAR 5320")
    instructor_list = await client.get(f"/api/v1/courses/{course}/instructors", headers=admin_headers)
    instructor_ids = [person["id"] for person in instructor_list.json()]
    assert len(instructor_ids) >= 2

    instructor_headers, instructor = await login(client, "joe.mota@utep.edu")
    target_user_id = next(user_id for user_id in instructor_ids if user_id != instructor["user"]["id"])
    other_instructor_removed = await client.delete(
        f"/api/v1/courses/{course}/roster/{target_user_id}",
        headers=instructor_headers,
        params={"role": "instructor"},
    )
    assert other_instructor_removed.status_code == 204

    self_remove = await client.delete(
        f"/api/v1/courses/{course}/roster/{instructor['user']['id']}",
        headers=instructor_headers,
        params={"role": "instructor"},
    )
    assert self_remove.status_code == 409

    student_headers, _ = await login(client, "daniel.reyes@miners.utep.edu")
    student_attempt = await client.delete(
        f"/api/v1/courses/{course}/roster/{target_user_id}",
        headers=student_headers,
        params={"role": "instructor"},
    )
    assert student_attempt.status_code == 403


@pytest.mark.asyncio
async def test_cannot_remove_last_instructor(client):
    admin_headers, _ = await login(client, "gerardo.sillas@utep.edu")
    joe_headers, joe = await login(client, "joe.mota@utep.edu")
    course = await course_id(client, admin_headers, "PHAR 5320")
    instructors = await client.get(f"/api/v1/courses/{course}/instructors", headers=admin_headers)
    assert instructors.status_code == 200, instructors.text
    joe_id = joe["user"]["id"]
    other_instructor_ids = [person["id"] for person in instructors.json() if person["id"] != joe_id]
    assert other_instructor_ids

    for instructor_id in other_instructor_ids:
        removed = await client.delete(
            f"/api/v1/courses/{course}/roster/{instructor_id}",
            headers=joe_headers,
            params={"role": "instructor"},
        )
        assert removed.status_code == 204, removed.text

    remaining = await client.get(f"/api/v1/courses/{course}/instructors", headers=admin_headers)
    assert remaining.status_code == 200, remaining.text
    assert len(remaining.json()) == 1
    assert remaining.json()[0]["id"] == joe_id

    final_removal = await client.delete(
        f"/api/v1/courses/{course}/roster/{joe_id}",
        headers=admin_headers,
        params={"role": "instructor"},
    )
    assert final_removal.status_code == 409
    assert "at least one instructor" in final_removal.json()["detail"]

    remaining_after_rejection = await client.get(f"/api/v1/courses/{course}/instructors", headers=admin_headers)
    assert remaining_after_rejection.status_code == 200, remaining_after_rejection.text
    assert len(remaining_after_rejection.json()) == 1
    assert remaining_after_rejection.json()[0]["id"] == joe_id


@pytest.mark.asyncio
async def test_ended_course_rejects_writes(client):
    admin_headers, _ = await login(client, "gerardo.sillas@utep.edu")
    course = await course_id(client, admin_headers, "PHAR 5320")
    student_headers, _ = await login(client, "daniel.reyes@miners.utep.edu")
    rosa = await patient_by_mrn(client, student_headers, course, "student", "TR-20001")

    payload = {"encounter": "In progress"}
    allowed = await client.patch(
        f"/api/v1/patients/{rosa['id']}/status",
        headers=student_headers,
        params={"role": "student"},
        json=payload,
    )
    assert allowed.status_code == 200, allowed.text

    ended = await client.post(f"/api/v1/courses/{course}/status", headers=admin_headers, json={"status": "ended"})
    assert ended.status_code == 200

    blocked = await client.patch(
        f"/api/v1/patients/{rosa['id']}/status",
        headers=student_headers,
        params={"role": "student"},
        json=payload,
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "This course has ended and cannot be edited."


@pytest.mark.asyncio
async def test_archived_courses_are_hidden_from_non_admins(client):
    admin_headers, _ = await login(client, "gerardo.sillas@utep.edu")
    created = await client.post(
        "/api/v1/courses",
        headers=admin_headers,
        json={"code": "TEST 3000", "title": "Archived Visibility", "term": "Fall 2026"},
    )
    assert created.status_code == 201, created.text
    course_id_value = created.json()["id"]
    for status in ["active", "ended", "archived"]:
        response = await client.post(
            f"/api/v1/courses/{course_id_value}/status",
            headers=admin_headers,
            json={"status": status},
        )
        assert response.status_code == 200, response.text

    student_headers, _ = await login(client, "daniel.reyes@miners.utep.edu")
    student_list = await client.get("/api/v1/courses", headers=student_headers)
    assert all(item["id"] != course_id_value for item in student_list.json())

    admin_list = await client.get("/api/v1/courses", headers=admin_headers)
    assert any(item["id"] == course_id_value and item["status"] == "archived" for item in admin_list.json())


@pytest.mark.asyncio
async def test_deactivated_user_cannot_login_until_reactivated(client):
    admin_headers, admin = await login(client, "gerardo.sillas@utep.edu")
    deactivate = await client.patch(
        f"/api/v1/users/{admin['user']['id']}/active",
        headers=admin_headers,
        json={"isActive": False},
    )
    assert deactivate.status_code == 409

    student_headers, student = await login(client, "daniel.reyes@miners.utep.edu")
    user_id = student["user"]["id"]
    disabled = await client.patch(
        f"/api/v1/users/{user_id}/active",
        headers=admin_headers,
        json={"isActive": False},
    )
    assert disabled.status_code == 200

    old_token_me = await client.get("/api/v1/auth/me", headers=student_headers)
    assert old_token_me.status_code == 401

    denied = await client.post(
        "/api/v1/auth/login",
        data={"username": "daniel.reyes@miners.utep.edu", "password": DEMO},
    )
    assert denied.status_code == 401

    restored = await client.patch(
        f"/api/v1/users/{user_id}/active",
        headers=admin_headers,
        json={"isActive": True},
    )
    assert restored.status_code == 200

    restored_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "daniel.reyes@miners.utep.edu", "password": DEMO},
    )
    assert restored_login.status_code == 200


@pytest.mark.asyncio
async def test_student_cannot_manage_courses_or_users(client):
    course_headers, _ = await login(client, "gerardo.sillas@utep.edu")
    course = await course_id(client, course_headers, "PHAR 5320")
    student_headers, student = await login(client, "daniel.reyes@miners.utep.edu")
    instructor_headers, _ = await login(client, "joe.mota@utep.edu")

    for headers in (student_headers, instructor_headers):
        created = await client.post(
            "/api/v1/courses",
            headers=headers,
            json={"code": "DENIED 1000", "title": "Denied Course", "term": "Fall 2026"},
        )
        assert created.status_code == 403

        status_update = await client.post(
            f"/api/v1/courses/{course}/status", headers=headers, json={"status": "ended"}
        )
        assert status_update.status_code == 403

        user_update = await client.patch(
            f"/api/v1/users/{student['user']['id']}/active",
            headers=headers,
            json={"isActive": False},
        )
        assert user_update.status_code == 403

        report = await client.get(f"/api/v1/reports/courses/{course}", headers=headers)
        assert report.status_code == 403


@pytest.mark.asyncio
async def test_instructor_cannot_import_instructors(client):
    instructor_headers, _ = await login(client, "joe.mota@utep.edu")
    course = await course_id(client, instructor_headers, "PHAR 5320")
    response = await client.post(
        f"/api/v1/courses/{course}/roster/import",
        headers=instructor_headers,
        json={
            "discipline": "pharmacy",
            "role": "instructor",
            "rows": [
                {
                    "fullName": "Valid Instructor",
                    "email": "valid.instructor@miners.utep.edu",
                    "universityId": "800900004",
                }
            ],
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_student_advances_encounter_but_cannot_reset(client):
    headers, _ = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, headers, "PHAR 5320")
    rosa = await patient_by_mrn(client, headers, course, "student", "TR-20001")
    blocked = await client.patch(
        f"/api/v1/patients/{rosa['id']}/status",
        headers=headers,
        params={"role": "student"},
        json={"lifecycle": "Inactive"},
    )
    assert blocked.status_code == 403
    moved = await client.patch(
        f"/api/v1/patients/{rosa['id']}/status",
        headers=headers,
        params={"role": "student"},
        json={"encounter": "In progress"},
    )
    assert moved.status_code == 200
    assert moved.json()["status"]["encounter"] == "In progress"
    reset = await client.post(f"/api/v1/patients/{rosa['id']}/reset", headers=headers, params={"role": "student"})
    assert reset.status_code == 403


@pytest.mark.asyncio
async def test_instructor_reset_restores_practice_chart(client):
    headers, _ = await login(client, "gerardo.sillas@utep.edu")
    course = await course_id(client, headers, "PHAR 5320")
    rosa = await patient_by_mrn(client, headers, course, "instructor", "TR-20001")
    await client.patch(
        f"/api/v1/patients/{rosa['id']}/status",
        headers=headers,
        params={"role": "instructor"},
        json={"encounter": "Checked out"},
    )
    reset = await client.post(f"/api/v1/patients/{rosa['id']}/reset", headers=headers, params={"role": "instructor"})
    assert reset.status_code == 204
    again = await client.get(f"/api/v1/patients/{rosa['id']}", headers=headers, params={"role": "instructor"})
    assert again.json()["status"]["encounter"] == "Checked in"
    assert any(med["name"] == "Lisinopril" for med in again.json()["medications"])


@pytest.mark.asyncio
async def test_note_sign_version_and_cosign(client):
    student, _ = await login(client, "daniel.reyes@miners.utep.edu")
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    course = await course_id(client, student, "PHAR 5320")
    rosa = await patient_by_mrn(client, student, course, "student", "TR-20001")
    created = await client.post(
        f"/api/v1/patients/{rosa['id']}/notes",
        headers=student,
        params={"role": "student"},
        json={"templateId": "pharmacy_mtm", "discipline": "pharmacy"},
    )
    assert created.status_code == 200, created.text
    note_id = created.json()["id"]
    saved = await client.patch(
        f"/api/v1/notes/{note_id}",
        headers=student,
        params={"role": "student"},
        json={"expectedVersion": 1, "content": {"reason": "Blood pressure follow-up"}},
    )
    assert saved.status_code == 200
    assert saved.json()["version"] == 2
    stale = await client.patch(
        f"/api/v1/notes/{note_id}",
        headers=student,
        params={"role": "student"},
        json={"expectedVersion": 1, "content": {"reason": "stale"}},
    )
    assert stale.status_code == 409
    signed = await client.post(
        f"/api/v1/notes/{note_id}/sign",
        headers=student,
        params={"role": "student"},
        json={"expectedVersion": 2},
    )
    assert signed.status_code == 200
    assert signed.json()["status"] == "signed"

    sam = await patient_by_mrn(client, instructor, course, "instructor", "TR-10057-ST")
    meds = {item["name"] for item in sam["medications"]}
    assert meds == {"Metformin", "Multivitamin"}
    queue = await client.get("/api/v1/review-queue", headers=instructor, params={"course_id": course, "role": "instructor"})
    assert queue.status_code == 200
    pending = next(item for item in queue.json() if item["patient"]["mrn"] == "TR-10057-ST")
    denied = await client.post(
        f"/api/v1/notes/{pending['note']['id']}/cosign",
        headers=student,
        params={"role": "student"},
        json={"comment": "no"},
    )
    assert denied.status_code == 403
    cosigned = await client.post(
        f"/api/v1/notes/{pending['note']['id']}/cosign",
        headers=instructor,
        params={"role": "instructor"},
        json={"comment": "Plan is appropriate."},
    )
    assert cosigned.status_code == 200, cosigned.text
    assert cosigned.json()["status"] == "cosigned"
    assert cosigned.json()["cosignedByName"] == "Gerardo Sillas"


@pytest.mark.asyncio
async def test_return_and_resubmit(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    sam_headers, _ = await login(client, "sam.torres@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    queue = await client.get("/api/v1/review-queue", headers=instructor, params={"course_id": course, "role": "instructor"})
    pending = next(item["note"] for item in queue.json() if item["note"]["status"] == "pending_review")
    returned = await client.post(
        f"/api/v1/notes/{pending['id']}/return",
        headers=instructor,
        params={"role": "instructor"},
        json={"comment": "Address adherence."},
    )
    assert returned.status_code == 200
    assert returned.json()["status"] == "returned"
    resigned = await client.post(
        f"/api/v1/notes/{pending['id']}/sign",
        headers=sam_headers,
        params={"role": "student"},
        json={"expectedVersion": returned.json()["version"]},
    )
    assert resigned.status_code == 200, resigned.text
    assert resigned.json()["status"] == "pending_review"
    queue_after = await client.get("/api/v1/review-queue", headers=instructor, params={"course_id": course, "role": "instructor"})
    statuses = {item["note"]["status"] for item in queue_after.json()}
    assert "pending_review" in statuses
    assert "returned" in statuses or "cosigned" in statuses


@pytest.mark.asyncio
async def test_roster_import_and_audit(client):
    headers, _ = await login(client, "gerardo.sillas@utep.edu")
    course = await course_id(client, headers, "PHAR 5320")
    imported = await client.post(
        f"/api/v1/courses/{course}/roster/import",
        headers=headers,
        params={"role": "instructor"},
        json={
            "discipline": "pharmacy",
            "rows": [{"fullName": "New Student", "email": "new.student@miners.utep.edu", "universityId": "800999999"}],
        },
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["added"] == 1
    assert imported.json()["temporaryPasswords"][0]["email"] == "new.student@miners.utep.edu"
    again = await client.post(
        f"/api/v1/courses/{course}/roster/import",
        headers=headers,
        params={"role": "instructor"},
        json={
            "discipline": "pharmacy",
            "rows": [{"fullName": "New Student", "email": "new.student@miners.utep.edu", "universityId": "800999999"}],
        },
    )
    assert again.json()["alreadyEnrolled"] == 1
    student, _ = await login(client, "daniel.reyes@miners.utep.edu")
    hidden = await client.get("/api/v1/audit", headers=student, params={"course_id": course, "role": "student"})
    assert hidden.status_code == 403
    audit = await client.get("/api/v1/audit", headers=headers, params={"course_id": course, "role": "instructor"})
    assert audit.status_code == 200
    actions = {item["action"] for item in audit.json()}
    assert "roster.import" in actions
    assert "chart.view" in actions


@pytest.mark.asyncio
async def test_instructor_assigns_and_unassigns_assessment_copy(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    student, me = await login(client, "daniel.reyes@miners.utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    source = await patient_by_mrn(client, instructor, course, "instructor", "TR-20003")

    blocked = await client.post(
        "/api/v1/patients",
        headers=student,
        params={"course_id": course, "role": "student"},
        json={"sourcePatientId": source["id"], "ownerId": me["user"]["id"]},
    )
    assert blocked.status_code == 403

    assigned = await client.post(
        "/api/v1/patients",
        headers=instructor,
        params={"course_id": course, "role": "instructor"},
        json={"sourcePatientId": source["id"], "ownerId": me["user"]["id"]},
    )
    assert assigned.status_code == 200, assigned.text
    body = assigned.json()
    assert body["ownerId"] == me["user"]["id"]
    listed = await client.get("/api/v1/patients", headers=student, params={"course_id": course, "role": "student"})
    assert body["id"] in {row["patient"]["id"] for row in listed.json()}

    again = await client.post(
        "/api/v1/patients",
        headers=instructor,
        params={"course_id": course, "role": "instructor"},
        json={"sourcePatientId": source["id"], "ownerId": me["user"]["id"]},
    )
    assert again.status_code == 409

    removed = await client.delete(
        f"/api/v1/patients/{body['id']}",
        headers=instructor,
        params={"role": "instructor"},
    )
    assert removed.status_code == 204
    after = await client.get("/api/v1/patients", headers=student, params={"course_id": course, "role": "student"})
    assert body["id"] not in {row["patient"]["id"] for row in after.json()}

    reassigned = await client.post(
        "/api/v1/patients",
        headers=instructor,
        params={"course_id": course, "role": "instructor"},
        json={"sourcePatientId": source["id"], "ownerId": me["user"]["id"]},
    )
    assert reassigned.status_code == 200, reassigned.text
