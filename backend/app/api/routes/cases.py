import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, Request, Response, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.clinical import AnswerKeyIn, AnswerKeyOut, CaseCopyIn, CaseIn, CaseOut, PatientOut, StartSimulation, TriggersIn, TriggersOut
from app.services.access import can, ensure_course_open, memberships_for, require_course
from app.services.answer_keys import deny_answer_key, read_answer_key, upsert_answer_key
from app.services.audit import log_event
from app.services.case_import import import_cases, template_workbook
from app.services.cases import copy_case, create_case, list_cases, load_case, save_case_rubric, save_triggers, update_case
from app.services.serialize import authored_case_out, patient_out
from app.services.charts import owner_name_for
from app.services.simulation import start_simulation

router = APIRouter(prefix="/cases", tags=["cases"])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _require_author(db, user, role: str, rows, course_id: uuid.UUID, request: Request, action: str) -> None:
    require_course(role, course_id, user, rows)
    if can(role, "case:author"):
        return
    await log_event(
        db,
        action=action,
        entity_type="patient",
        entity_id=str(course_id),
        actor_user_id=user.id,
        result="denied",
        course_id=course_id,
        ip_address=_ip(request),
        detail="Role cannot author cases.",
    )
    await db.commit()
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role can't author cases.")


@router.get("", response_model=list[CaseOut], response_model_exclude_none=True)
async def get_cases(
    db: DbSession,
    user: CurrentUser,
    request: Request,
    course_id: Annotated[uuid.UUID, Query()],
    role: Annotated[str, Query()],
):
    rows = await memberships_for(db, user.id)
    await _require_author(db, user, role, rows, course_id, request, "case.list")
    cases = await list_cases(db, course_id)
    return [authored_case_out(case) for case in cases]


@router.post("", response_model=CaseOut, response_model_exclude_none=True)
async def post_case(
    body: CaseIn,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    course_id: Annotated[uuid.UUID, Query()],
    role: Annotated[str, Query()],
):
    rows = await memberships_for(db, user.id)
    await _require_author(db, user, role, rows, course_id, request, "case.create")
    await ensure_course_open(db, course_id)
    patient = await create_case(db, body=body, actor=user, course_id=course_id, ip=_ip(request))
    await db.commit()
    return authored_case_out(patient)


@router.get("/import-template")
async def download_case_template(
    db: DbSession,
    user: CurrentUser,
    request: Request,
    course_id: Annotated[uuid.UUID, Query()],
    role: Annotated[str, Query()],
):
    rows = await memberships_for(db, user.id)
    await _require_author(db, user, role, rows, course_id, request, "case.template")
    return Response(
        template_workbook(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Patient_Case_Upload_Template.xlsx"'},
    )


@router.post("/import")
async def post_case_import(
    db: DbSession,
    user: CurrentUser,
    request: Request,
    course_id: Annotated[uuid.UUID, Query()],
    role: Annotated[str, Query()],
    file: UploadFile = File(...),
):
    rows = await memberships_for(db, user.id)
    await _require_author(db, user, role, rows, course_id, request, "case.import")
    await ensure_course_open(db, course_id)
    result = await import_cases(
        db, payload=await file.read(), actor=user, course_id=course_id, ip=_ip(request),
    )
    await db.commit()
    return result


@router.post("/{case_id}/simulations", response_model=PatientOut, response_model_exclude_none=True)
async def post_simulation(
    case_id: uuid.UUID,
    body: StartSimulation,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    course_id: Annotated[uuid.UUID, Query()],
    role: Annotated[str, Query()],
):
    source = await load_case(db, case_id)
    rows = await memberships_for(db, user.id)
    await _require_author(db, user, role, rows, course_id, request, "simulation.start")
    await ensure_course_open(db, course_id)
    clone = await start_simulation(
        db,
        source=source,
        actor=user,
        role=role,
        course_id=course_id,
        nurse_id=body.nurse_id,
        pharmacist_id=body.pharmacist_id,
        provider_id=body.provider_id,
        ip=_ip(request),
    )
    await db.commit()
    return patient_out(clone, owner_name=owner_name_for(clone, role), viewer_role=role)


@router.get("/{case_id}", response_model=CaseOut, response_model_exclude_none=True)
async def get_case(
    case_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_case(db, case_id)
    rows = await memberships_for(db, user.id)
    await _require_author(db, user, role, rows, patient.course_id, request, "case.view")
    await log_event(
        db,
        action="case.view",
        entity_type="patient",
        entity_id=str(patient.id),
        actor_user_id=user.id,
        course_id=patient.course_id,
        ip_address=_ip(request),
    )
    await db.commit()
    return authored_case_out(patient)


@router.patch("/{case_id}", response_model=CaseOut, response_model_exclude_none=True)
async def patch_case(
    case_id: uuid.UUID,
    body: CaseIn,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_case(db, case_id)
    rows = await memberships_for(db, user.id)
    await _require_author(db, user, role, rows, patient.course_id, request, "case.update")
    await ensure_course_open(db, patient.course_id)
    updated = await update_case(db, patient=patient, body=body, actor=user, ip=_ip(request))
    await db.commit()
    return authored_case_out(updated)


@router.get("/{case_id}/answer-key", response_model=AnswerKeyOut, response_model_exclude_none=True)
async def get_case_answer_key(
    case_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_case(db, case_id)
    rows = await memberships_for(db, user.id)
    await deny_answer_key(
        db, user=user, role=role, rows=rows, course_id=patient.course_id,
        entity_id=str(patient.id), ip=_ip(request), action="answer_key.view",
    )
    payload = await read_answer_key(db, patient)
    await log_event(
        db, action="answer_key.view", entity_type="patient", entity_id=str(patient.id),
        actor_user_id=user.id, course_id=patient.course_id, ip_address=_ip(request),
    )
    await db.commit()
    return payload


@router.put("/{case_id}/answer-key", response_model=AnswerKeyOut, response_model_exclude_none=True)
async def put_case_answer_key(
    case_id: uuid.UUID,
    body: AnswerKeyIn,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_case(db, case_id)
    rows = await memberships_for(db, user.id)
    await deny_answer_key(
        db, user=user, role=role, rows=rows, course_id=patient.course_id,
        entity_id=str(patient.id), ip=_ip(request), action="answer_key.update",
    )
    await ensure_course_open(db, patient.course_id)
    payload = await upsert_answer_key(db, patient, body, user)
    await log_event(
        db, action="answer_key.update", entity_type="patient", entity_id=str(patient.id),
        actor_user_id=user.id, course_id=patient.course_id, ip_address=_ip(request),
    )
    await db.commit()
    return payload


@router.post("/{case_id}/rubric")
async def post_case_rubric(
    case_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
    file: UploadFile = File(...),
):
    patient = await load_case(db, case_id)
    rows = await memberships_for(db, user.id)
    await _require_author(db, user, role, rows, patient.course_id, request, "case.grading_guide")
    await ensure_course_open(db, patient.course_id)
    guide = await save_case_rubric(db, patient, file.filename or "rubric.pdf", await file.read())
    await log_event(
        db, action="case.grading_guide", entity_type="patient", entity_id=str(patient.id),
        actor_user_id=user.id, course_id=patient.course_id, ip_address=_ip(request),
        detail=guide.get("file_name"),
    )
    await db.commit()
    return guide


@router.put("/{case_id}/triggers", response_model=TriggersOut, response_model_exclude_none=True)
async def put_case_triggers(
    case_id: uuid.UUID,
    body: TriggersIn,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_case(db, case_id)
    rows = await memberships_for(db, user.id)
    await _require_author(db, user, role, rows, patient.course_id, request, "case.triggers")
    await ensure_course_open(db, patient.course_id)
    saved = await save_triggers(db, patient, body.triggers)
    await log_event(
        db, action="case.triggers", entity_type="patient", entity_id=str(patient.id),
        actor_user_id=user.id, course_id=patient.course_id, ip_address=_ip(request),
        detail=f"{len(saved)} planted findings",
    )
    await db.commit()
    return {"triggers": saved}


@router.post("/{case_id}/copy", response_model=CaseOut, response_model_exclude_none=True)
async def post_case_copy(
    case_id: uuid.UUID,
    body: CaseCopyIn,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_case(db, case_id)
    rows = await memberships_for(db, user.id)
    await _require_author(db, user, role, rows, patient.course_id, request, "case.copy")
    clone = await copy_case(
        db, patient=patient, destination_id=body.course_id, actor=user, rows=rows, ip=_ip(request),
    )
    await db.commit()
    return authored_case_out(clone)
