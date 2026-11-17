from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession
from app.services.reference_data import (
    lexicomp_interactions,
    lexicomp_status,
    medication_details,
    search_cpt,
    search_icd10,
    search_medications,
)

router = APIRouter(prefix="/reference", tags=["reference"])


@router.get("/icd10")
async def icd10(user: CurrentUser, q: Annotated[str, Query()] = ""):
    return await search_icd10(q)


@router.get("/medications")
async def medications(user: CurrentUser, q: Annotated[str, Query()] = ""):
    return await search_medications(q)


@router.get("/medications/{rxcui}")
async def medication(user: CurrentUser, rxcui: str):
    return await medication_details(rxcui)


@router.get("/cpt")
async def cpt(user: CurrentUser, q: Annotated[str, Query()] = ""):
    return search_cpt(q)


class LexicompCheck(BaseModel):
    medications: list[str] = Field(default_factory=list)


@router.get("/lexicomp")
async def lexicomp(user: CurrentUser):
    return lexicomp_status()


@router.post("/lexicomp/interactions")
async def lexicomp_check(body: LexicompCheck, user: CurrentUser):
    return await lexicomp_interactions(body.medications)
