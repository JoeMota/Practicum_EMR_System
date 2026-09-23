"""Pydantic schemas shaped to match frontend/src/types so the React api/*
modules can map 1:1 without reshaping in every feature."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RoleAssignmentOut(BaseModel):
    role: str
    discipline: str | None = None
    courseIds: list[str]


class SessionUserOut(BaseModel):
    """Frontend User shape."""

    id: str
    fullName: str
    email: EmailStr
    universityId: str | None = None
    phoneLast4: str | None = None
    roles: list[RoleAssignmentOut]
    mustChangePassword: bool = False


class ChallengeStartRequest(BaseModel):
    email: EmailStr
    password: str


class ChallengeStartResponse(BaseModel):
    challengeId: str
    phoneLast4: str | None = None
    emailMasked: str


class SendCodeRequest(BaseModel):
    challengeId: str
    channel: Literal["sms", "email"]


class VerifyCodeRequest(BaseModel):
    challengeId: str
    code: str = Field(min_length=4, max_length=12)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool
    user: SessionUserOut


class CourseOut(BaseModel):
    id: str
    code: str
    title: str
    term: str
    instructorIds: list[str]
    rubricFileName: str | None = None


class PatientStatusIn(BaseModel):
    lifecycle: str | None = None
    encounter: str | None = None
    careSetting: str | None = None
    program: str | None = None


class PatientOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    mrn: str
    firstName: str
    lastName: str
    preferredName: str | None = None
    dob: str
    ageYears: int
    sexAtBirth: str
    pronouns: str | None = None
    courseId: str
    mode: str
    caseTemplateId: str
    ownerId: str | None = None
    ownerName: str | None = None
    isTraining: bool = True
    practiceLabel: str | None = None
    chiefComplaint: str
    hpi: str
    status: dict[str, Any]
    allergies: list[Any]
    medications: list[Any]
    problems: list[Any]
    labs: list[Any]
    vitals: list[Any]
    familyHistory: str
    surgicalHistory: str
    socialHistory: str
    encounter: dict[str, Any]


class PatientRowOut(BaseModel):
    patient: PatientOut
    ownerName: str | None = None
    latestNote: dict[str, Any] | None = None


class DraftPatchIn(BaseModel):
    templateId: str | None = None
    content: dict[str, str] | None = None
    diagnoses: list[dict[str, str]] | None = None
    routedToId: str | None = None
    expectedVersion: int


class CreateNoteIn(BaseModel):
    patientId: str
    templateId: str
    discipline: str


class NoteActionIn(BaseModel):
    expectedVersion: int | None = None
    comment: str | None = None
    body: str | None = None


class ClinicalNoteOut(BaseModel):
    id: str
    patientId: str
    encounterId: str
    templateId: str
    authorId: str
    authorName: str
    authorDiscipline: str
    mode: str
    status: str
    version: int
    content: dict[str, Any]
    diagnoses: list[Any]
    routedToId: str | None = None
    createdAt: str
    updatedAt: str
    signedAt: str | None = None
    cosignedAt: str | None = None
    cosignedByName: str | None = None
    feedback: list[Any]
    addenda: list[Any]


class QueueItemOut(BaseModel):
    note: ClinicalNoteOut
    patient: PatientOut


class RosterImportIn(BaseModel):
    discipline: str
    rows: list[dict[str, str]]


class RosterImportOut(BaseModel):
    added: int
    alreadyEnrolled: int


class AuditEntryOut(BaseModel):
    id: str
    timestamp: str
    actorId: str
    actorName: str
    action: str
    entity: str
    result: Literal["ok", "denied"]
    detail: str | None = None


class AppointmentOut(BaseModel):
    id: str
    patientId: str
    when: str
    kind: str
    withWhom: str


class ReferralIn(BaseModel):
    patientId: str
    toDiscipline: str
    reason: str
    urgency: Literal["routine", "urgent"] = "routine"


class ReferralOut(BaseModel):
    id: str
    patientId: str
    toDiscipline: str
    reason: str
    urgency: str
    createdByName: str
    createdAt: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
