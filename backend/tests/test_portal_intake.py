from datetime import datetime, timedelta, timezone
import uuid

import pytest
from sqlalchemy import select

from app.models.audit import AuditEvent
from app.models.clinical import Course, Patient, PatientIntake
from app.models.user import User
from app.services.hidden import assert_no_hidden
from app.services.retention import purge_expired
from tests.test_portal import _portal_headers
from tests.test_workflows import course_id, login, patient_by_mrn


def intake_payload(**updates):
    data = {
        "preferredName": "Rosie",
        "pronouns": "she/her",
        "phone": "915-555-0101",
        "address": "100 Demo Street, El Paso, TX",
        "preferredLanguage": "English",
        "pastMedicalHistory": "Fictional hypertension history.",
        "surgicalHistory": "Fictional appendectomy.",
        "familyHistory": "Fictional family history.",
        "socialHistory": "Fictional social history.",
        "insurancePayer": "Example Health Plan",
        "insuranceMemberId": "DEMO-MEMBER-100",
        "insuranceGroupNumber": "DEMO-GROUP-10",
        "emergencyContactName": "Rosa Demo Contact",
        "emergencyContactPhone": "915-555-0102",
        "emergencyContactRelationship": "Family",
    }
    return {**data, **updates}


def full_v2_payload(**updates):
    data = {
        **intake_payload(),
        "genderIdentity": "Woman",
        "race": ["Asian", "White"],
        "ethnicity": "Hispanic or Latino",
        "maritalStatus": "Married",
        "interpreterNeeded": False,
        "email": "rosa@example.test",
        "phoneType": "Mobile",
        "city": "El Paso",
        "state": "TX",
        "zipCode": "79901-1234",
        "insurancePlanType": "PPO",
        "insuranceSubscriberIsPatient": False,
        "insuranceSubscriberName": "Rosa Demo Subscriber",
        "insuranceSubscriberDob": "1970-01-02",
        "insuranceRelationship": "Spouse",
        "insuranceEffectiveDate": "2025-01-01",
        "secondaryInsurancePayer": "Secondary Example Plan",
        "secondaryInsuranceMemberId": "SECONDARY-MEMBER-20",
        "secondaryInsuranceGroupNumber": "SECONDARY-GROUP-2",
        "secondaryInsuranceRelationship": "Self",
        "conditions": [{"name": "Asthma", "year": "2018"}],
        "surgeries": [{"procedure": "Appendectomy", "year": "2010"}],
        "allergies": [{"agent": "Penicillin", "reaction": "Rash"}],
        "noKnownAllergies": False,
        "medications": [{"name": "Lisinopril", "dose": "10 mg", "frequency": "Daily"}],
        "familyMembers": [{"relative": "Mother", "status": "Living", "conditions": "Hypertension"}],
        "tobaccoUse": "Never",
        "tobaccoDetail": "",
        "alcoholUse": "Occasional",
        "alcoholDetail": "One drink monthly",
        "drugUse": "Never",
        "occupation": "Teacher",
        "livesWith": "Family",
        "exercise": "Walks weekly",
        "preferredPharmacy": "Example Pharmacy",
        "confirmedAccurate": True,
    }
    return {**data, **updates}


async def _rosa_context(client):
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    course = await course_id(client, instructor, "PHAR 5320")
    rosa = await patient_by_mrn(client, instructor, course, "instructor", "TR-20001")
    return instructor, course, rosa


@pytest.mark.asyncio
async def test_portal_intake_loads_chart_defaults_and_staff_sees_unsubmitted(client):
    patient, _ = await login(client, "patient.demo@example.com")
    instructor, _, rosa = await _rosa_context(client)

    response = await client.get("/api/v1/portal/intake", headers=patient)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "chart"
    assert body["identity"] == {
        "firstName": "Rosa",
        "lastName": "Villalobos",
        "dob": "1958-07-02",
        "sexAtBirth": "Female",
        "mrn": "TR-20001",
    }
    assert body["data"]["preferredName"] == "Rosie"
    assert body["editable"] is True
    assert body["updatedAt"] is None
    assert_no_hidden(body)

    staff = await client.get(
        f"/api/v1/patients/{rosa['id']}/intake", headers=instructor, params={"role": "instructor"},
    )
    assert staff.status_code == 200, staff.text
    assert staff.json() == {"submitted": False, "data": None, "updatedAt": None}
    assert_no_hidden(staff.json())


@pytest.mark.asyncio
async def test_portal_intake_saves_edits_and_upserts_one_row(client, db_session):
    patient, _ = await login(client, "patient.demo@example.com")
    instructor, _, rosa = await _rosa_context(client)

    first = await client.put("/api/v1/portal/intake", headers=patient, params={"role": "patient"}, json=intake_payload())
    assert first.status_code == 200, first.text
    saved = first.json()
    assert saved["source"] == "patient"
    assert saved["data"]["preferredName"] == "Rosie"
    assert saved["updatedAt"] is not None
    assert_no_hidden(saved)

    changed = await client.put(
        "/api/v1/portal/intake", headers=patient, params={"role": "patient"},
        json=intake_payload(preferredName="Rosa D."),
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["data"]["preferredName"] == "Rosa D."
    assert changed.json()["source"] == "patient"
    rows = list((await db_session.scalars(select(PatientIntake).where(PatientIntake.patient_id == uuid.UUID(rosa["id"])))).all())
    assert len(rows) == 1

    staff = await client.get(
        f"/api/v1/patients/{rosa['id']}/intake", headers=instructor, params={"role": "instructor"},
    )
    assert staff.status_code == 200, staff.text
    assert staff.json()["submitted"] is True
    assert staff.json()["data"]["preferredName"] == "Rosa D."


@pytest.mark.asyncio
async def test_portal_intakes_are_isolated_between_linked_patients(client, db_session):
    instructor, course, rosa = await _rosa_context(client)
    elena = await patient_by_mrn(client, instructor, course, "instructor", "TR-20003")
    rosa_headers, _ = await _portal_headers(client, db_session, rosa["id"], "intake-rosa")
    elena_headers, _ = await _portal_headers(client, db_session, elena["id"], "intake-elena")

    forged = await client.put(
        "/api/v1/portal/intake", headers=rosa_headers,
        json=intake_payload(patientId=elena["id"]),
    )
    assert forged.status_code == 422

    rosa_write = await client.put(
        "/api/v1/portal/intake", headers=rosa_headers,
        json=intake_payload(preferredName="Rosa Only"),
    )
    elena_write = await client.put(
        "/api/v1/portal/intake", headers=elena_headers,
        json=intake_payload(preferredName="Elena Only"),
    )
    assert rosa_write.status_code == elena_write.status_code == 200

    rosa_read = await client.get("/api/v1/portal/intake", headers=rosa_headers)
    elena_read = await client.get("/api/v1/portal/intake", headers=elena_headers)
    assert rosa_read.json()["identity"]["mrn"] == "TR-20001"
    assert elena_read.json()["identity"]["mrn"] == "TR-20003"
    assert rosa_read.json()["data"]["preferredName"] == "Rosa Only"
    assert elena_read.json()["data"]["preferredName"] == "Elena Only"


@pytest.mark.asyncio
async def test_nonpatient_roles_and_unlinked_patient_are_denied(client, db_session):
    student, _ = await login(client, "daniel.reyes@miners.utep.edu")
    instructor, _ = await login(client, "gerardo.sillas@utep.edu")
    admin, _ = await login(client, "clarissa.dominguez@utep.edu")
    body = intake_payload()
    for headers in (student, instructor, admin):
        assert (await client.get("/api/v1/portal/intake", headers=headers)).status_code == 403
        assert (await client.put("/api/v1/portal/intake", headers=headers, json=body)).status_code == 403

    unlinked, _ = await _portal_headers(client, db_session, None, "intake-unlinked")
    assert (await client.get("/api/v1/portal/intake", headers=unlinked)).status_code == 404
    assert (await client.put("/api/v1/portal/intake", headers=unlinked, json=body)).status_code == 404


@pytest.mark.asyncio
async def test_case_master_intake_is_not_editable(client, db_session):
    case = await db_session.scalar(select(Patient).where(Patient.mode == "case"))
    assert case is not None
    patient, _ = await _portal_headers(client, db_session, case.id, "intake-case")

    read = await client.get("/api/v1/portal/intake", headers=patient)
    assert read.status_code == 200, read.text
    assert read.json()["editable"] is False
    assert read.json()["notEditableReason"] == "Portal information is not available on case masters."
    write = await client.put("/api/v1/portal/intake", headers=patient, json=intake_payload())
    assert write.status_code == 409


@pytest.mark.asyncio
async def test_ended_and_archived_courses_disable_intake_edits(client, db_session):
    patient, _ = await login(client, "patient.demo@example.com")
    _, _, rosa = await _rosa_context(client)
    course = await db_session.scalar(select(Course).where(Course.id == uuid.UUID(rosa["courseId"])))
    assert course is not None

    for state in ("ended", "archived"):
        course.status = state
        await db_session.flush()
        read = await client.get("/api/v1/portal/intake", headers=patient)
        assert read.status_code == 200, read.text
        assert read.json()["editable"] is False
        assert read.json()["notEditableReason"] == "This course has ended and cannot be edited."
        write = await client.put("/api/v1/portal/intake", headers=patient, json=intake_payload())
        assert write.status_code == 409
    course.status = "active"
    await db_session.flush()


@pytest.mark.asyncio
async def test_intake_validation_trims_values_and_blank_clears_field(client):
    patient, _ = await login(client, "patient.demo@example.com")

    oversized = await client.put(
        "/api/v1/portal/intake", headers=patient,
        json=intake_payload(address="x" * 301),
    )
    assert oversized.status_code == 422
    unknown = await client.put(
        "/api/v1/portal/intake", headers=patient,
        json=intake_payload(unknownField="not accepted"),
    )
    assert unknown.status_code == 422

    trimmed = await client.put(
        "/api/v1/portal/intake", headers=patient,
        json=intake_payload(preferredName="  Rosie Demo  "),
    )
    assert trimmed.status_code == 200, trimmed.text
    assert trimmed.json()["data"]["preferredName"] == "Rosie Demo"
    cleared = await client.put(
        "/api/v1/portal/intake", headers=patient,
        json=intake_payload(preferredName=""),
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["data"]["preferredName"] == ""


@pytest.mark.asyncio
async def test_staff_visibility_and_assessment_ownership(client):
    patient_headers, _ = await login(client, "patient.demo@example.com")
    instructor, course, rosa = await _rosa_context(client)
    saved = await client.put(
        "/api/v1/portal/intake", headers=patient_headers,
        json=intake_payload(preferredName="Staff Visible"),
    )
    assert saved.status_code == 200, saved.text

    instructor_read = await client.get(
        f"/api/v1/patients/{rosa['id']}/intake", headers=instructor, params={"role": "instructor"},
    )
    student, _ = await login(client, "daniel.reyes@miners.utep.edu")
    student_read = await client.get(
        f"/api/v1/patients/{rosa['id']}/intake", headers=student, params={"role": "student"},
    )
    assert instructor_read.status_code == student_read.status_code == 200
    assert instructor_read.json()["data"]["preferredName"] == "Staff Visible"
    assert student_read.json()["data"]["preferredName"] == "Staff Visible"
    assert_no_hidden(instructor_read.json())
    assert_no_hidden(student_read.json())

    other_student_chart = await patient_by_mrn(client, instructor, course, "instructor", "TR-10057-ST")
    denied = await client.get(
        f"/api/v1/patients/{other_student_chart['id']}/intake", headers=student, params={"role": "student"},
    )
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_intake_does_not_change_chart_and_survives_practice_reset(client, db_session):
    patient, _ = await login(client, "patient.demo@example.com")
    instructor, _, rosa = await _rosa_context(client)
    before = await client.get(
        f"/api/v1/patients/{rosa['id']}", headers=instructor, params={"role": "instructor"},
    )
    assert before.status_code == 200, before.text
    original = before.json()

    saved = await client.put(
        "/api/v1/portal/intake", headers=patient,
        json=intake_payload(familyHistory="Patient-only family history", insurancePayer="Patient-only plan"),
    )
    assert saved.status_code == 200, saved.text
    after = await client.get(
        f"/api/v1/patients/{rosa['id']}", headers=instructor, params={"role": "instructor"},
    )
    assert after.json()["familyHistory"] == original["familyHistory"]
    assert after.json()["insurance"] == original["insurance"]
    assert after.json()["dob"] == original["dob"]

    reset = await client.post(
        f"/api/v1/patients/{rosa['id']}/reset", headers=instructor, params={"role": "instructor"},
    )
    assert reset.status_code == 204, reset.text
    intake = await db_session.scalar(select(PatientIntake).where(PatientIntake.patient_id == uuid.UUID(rosa["id"])))
    assert intake is not None
    assert intake.data["family_history"] == "Patient-only family history"


@pytest.mark.asyncio
async def test_intake_update_audit_contains_field_names_not_values(client, db_session):
    patient_headers, _ = await login(client, "patient.demo@example.com")
    _, _, rosa = await _rosa_context(client)
    response = await client.put(
        "/api/v1/portal/intake", headers=patient_headers,
        json=intake_payload(preferredName="SECRET_NAME", familyHistory="SECRET_HISTORY"),
    )
    assert response.status_code == 200, response.text
    actor = await db_session.scalar(select(User).where(User.email == "patient.demo@example.com"))
    assert actor is not None
    event = await db_session.scalar(
        select(AuditEvent).where(
            AuditEvent.action == "portal.intake.update",
            AuditEvent.entity_id == rosa["id"],
            AuditEvent.actor_user_id == actor.id,
        )
    )
    assert event is not None
    detail = event.details["detail"]
    assert "preferred_name" in detail
    assert "family_history" in detail
    assert "SECRET_NAME" not in detail
    assert "SECRET_HISTORY" not in detail


@pytest.mark.asyncio
async def test_retention_purge_removes_intake_rows_written_by_user(client, db_session):
    instructor, _, rosa = await _rosa_context(client)
    patient_headers, user = await _portal_headers(client, db_session, rosa["id"], "intake-retention")
    response = await client.put(
        "/api/v1/portal/intake", headers=patient_headers, json=intake_payload(),
    )
    assert response.status_code == 200, response.text
    assert await db_session.scalar(
        select(PatientIntake.id).where(PatientIntake.updated_by_user_id == user.id)
    ) is not None

    user.archived_at = datetime.now(timezone.utc) - timedelta(days=800)
    await db_session.flush()
    assert await purge_expired(db_session) == 1
    assert await db_session.scalar(
        select(PatientIntake.id).where(PatientIntake.updated_by_user_id == user.id)
    ) is None
    assert instructor


@pytest.mark.asyncio
async def test_v2_legacy_intake_row_defaults_new_fields_and_accepts_update(client, db_session):
    patient_headers, _ = await login(client, "patient.demo@example.com")
    _, _, rosa = await _rosa_context(client)
    patient_user = await db_session.scalar(select(User).where(User.email == "patient.demo@example.com"))
    assert patient_user is not None
    legacy_data = {
        "preferred_name": "Legacy Rosa",
        "pronouns": "she/her",
        "phone": "915-555-0101",
        "address": "100 Demo Street",
        "preferred_language": "English",
        "past_medical_history": "Legacy condition",
        "surgical_history": "",
        "family_history": "Legacy family history",
        "social_history": "",
        "insurance_payer": "Legacy Plan",
        "insurance_member_id": "LEGACY-100",
        "insurance_group_number": "LEGACY-GROUP",
        "emergency_contact_name": "Legacy Contact",
        "emergency_contact_phone": "915-555-0102",
        "emergency_contact_relationship": "Family",
    }
    db_session.add(PatientIntake(
        patient_id=uuid.UUID(rosa["id"]), data=legacy_data, updated_by_user_id=patient_user.id,
    ))
    await db_session.flush()

    response = await client.get("/api/v1/portal/intake", headers=patient_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data"]["preferredName"] == "Legacy Rosa"
    assert body["data"]["pastMedicalHistory"] == "Legacy condition"
    assert body["data"]["genderIdentity"] == ""
    assert body["data"]["race"] == []
    assert body["data"]["conditions"] == []
    assert body["data"]["allergies"] == []
    assert body["data"]["familyMembers"] == []
    assert body["data"]["insuranceSubscriberIsPatient"] is True
    assert body["data"]["insuranceSubscriberDob"] is None

    saved = await client.put(
        "/api/v1/portal/intake", headers=patient_headers, json=full_v2_payload(preferredName="Updated Rosa"),
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["data"]["preferredName"] == "Updated Rosa"


@pytest.mark.asyncio
async def test_v2_full_round_trip_and_staff_visibility(client):
    patient_headers, _ = await login(client, "patient.demo@example.com")
    instructor, _, rosa = await _rosa_context(client)
    payload = full_v2_payload()

    saved = await client.put("/api/v1/portal/intake", headers=patient_headers, json=payload)
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["data"] == payload
    assert body["data"]["race"] == payload["race"]
    assert body["data"]["insuranceSubscriberDob"] == payload["insuranceSubscriberDob"]
    assert body["data"]["conditions"] == payload["conditions"]
    assert body["data"]["allergies"] == payload["allergies"]
    assert body["data"]["familyMembers"] == payload["familyMembers"]
    assert body["data"]["confirmedAccurate"] is True
    assert_no_hidden(body)

    patient_read = await client.get("/api/v1/portal/intake", headers=patient_headers)
    assert patient_read.status_code == 200
    assert patient_read.json()["data"] == body["data"]
    staff = await client.get(
        f"/api/v1/patients/{rosa['id']}/intake", headers=instructor, params={"role": "instructor"},
    )
    assert staff.status_code == 200, staff.text
    assert staff.json()["data"]["allergies"] == payload["allergies"]
    assert_no_hidden(staff.json())
    student, _ = await login(client, "daniel.reyes@miners.utep.edu")
    student_read = await client.get(
        f"/api/v1/patients/{rosa['id']}/intake", headers=student, params={"role": "student"},
    )
    assert student_read.status_code == 200, student_read.text
    assert student_read.json()["data"]["conditions"] == payload["conditions"]
    assert_no_hidden(student_read.json())


@pytest.mark.asyncio
async def test_v2_returning_patient_edits_keep_other_list_items(client, db_session):
    patient_headers, _ = await login(client, "patient.demo@example.com")
    _, _, rosa = await _rosa_context(client)
    payload = full_v2_payload(
        conditions=[{"name": "Asthma", "year": "2018"}, {"name": "Migraines", "year": "2021"}],
        allergies=[{"agent": "Penicillin", "reaction": "Rash"}, {"agent": "Latex", "reaction": "Hives"}],
    )
    first = await client.put("/api/v1/portal/intake", headers=patient_headers, json=payload)
    assert first.status_code == 200, first.text

    changed = {**payload, "preferredName": "Rosa Updated", "allergies": [payload["allergies"][0], {"agent": "Latex", "reaction": "Swelling"}]}
    second = await client.put("/api/v1/portal/intake", headers=patient_headers, json=changed)
    assert second.status_code == 200, second.text
    assert second.json()["data"]["preferredName"] == "Rosa Updated"
    assert second.json()["data"]["conditions"] == payload["conditions"]
    assert second.json()["data"]["allergies"][1]["reaction"] == "Swelling"
    rows = list((await db_session.scalars(
        select(PatientIntake).where(PatientIntake.patient_id == uuid.UUID(rosa["id"]))
    )).all())
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_v2_validation_rejects_bad_fields_and_accepts_empty_dates(client):
    patient_headers, _ = await login(client, "patient.demo@example.com")
    invalid_payloads = [
        full_v2_payload(state="Texas"),
        full_v2_payload(zipCode="7990"),
        full_v2_payload(email="not-an-email"),
        full_v2_payload(phone="555-ABC-1234"),
        full_v2_payload(conditions=[{"name": "Asthma", "year": "1899"}]),
        full_v2_payload(genderIdentity="Unknown"),
        full_v2_payload(allergies=[{"agent": "Penicillin", "reaction": "Rash", "extra": "no"}]),
        full_v2_payload(conditions=[{"name": "Asthma", "year": "2020"}] * 31),
        full_v2_payload(insuranceSubscriberDob="not-a-date"),
    ]
    for payload in invalid_payloads:
        response = await client.put("/api/v1/portal/intake", headers=patient_headers, json=payload)
        assert response.status_code == 422, response.text

    oversized = full_v2_payload(
        pastMedicalHistory="x" * 4000,
        surgicalHistory="x" * 4000,
        familyHistory="x" * 4000,
        socialHistory="x" * 4000,
        conditions=[{"name": "x" * 80, "year": "2020"}] * 30,
        surgeries=[{"procedure": "x" * 120, "year": "2020"}] * 20,
        allergies=[{"agent": "x" * 80, "reaction": "x" * 120}] * 20,
        medications=[{"name": "x" * 80, "dose": "x" * 60, "frequency": "x" * 60}] * 25,
        familyMembers=[{"relative": "Other", "conditions": "x" * 200}] * 15,
    )
    too_large = await client.put("/api/v1/portal/intake", headers=patient_headers, json=oversized)
    assert too_large.status_code == 422, too_large.text

    empty_dates = await client.put(
        "/api/v1/portal/intake", headers=patient_headers,
        json=full_v2_payload(insuranceSubscriberDob="", insuranceEffectiveDate=""),
    )
    assert empty_dates.status_code == 200, empty_dates.text
    assert empty_dates.json()["data"]["insuranceSubscriberDob"] is None
    assert empty_dates.json()["data"]["insuranceEffectiveDate"] is None


@pytest.mark.asyncio
async def test_v2_audit_detail_contains_names_but_no_submitted_values(client, db_session):
    patient_headers, _ = await login(client, "patient.demo@example.com")
    _, _, rosa = await _rosa_context(client)
    response = await client.put(
        "/api/v1/portal/intake", headers=patient_headers,
        json=full_v2_payload(insurancePayer="SECRET-CARRIER-123"),
    )
    assert response.status_code == 200, response.text
    event = await db_session.scalar(select(AuditEvent).where(
        AuditEvent.action == "portal.intake.update",
        AuditEvent.entity_id == rosa["id"],
    ))
    assert event is not None
    detail = event.details["detail"]
    assert "insurance_payer" in detail
    assert "allergies" in detail
    assert "SECRET-CARRIER-123" not in detail
