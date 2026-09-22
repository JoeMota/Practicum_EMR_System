"""Simulated patients (FR-11..FR-17). Chart sections live in JSONB so future
teams can extend fields without a migration for every discipline quirk."""
import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Patient(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "patients"

    mrn: Mapped[str] = mapped_column(String(50), index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    preferred_name: Mapped[str | None] = mapped_column(String(100))
    dob: Mapped[str] = mapped_column(String(20))  # ISO date string for educational data
    age_years: Mapped[int] = mapped_column(Integer)
    sex_at_birth: Mapped[str] = mapped_column(String(20))
    pronouns: Mapped[str | None] = mapped_column(String(40))

    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"), index=True)
    mode: Mapped[str] = mapped_column(String(20))  # practice | assessment
    case_template_id: Mapped[str] = mapped_column(String(80))
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    is_training: Mapped[bool] = mapped_column(Boolean, default=True)
    practice_label: Mapped[str | None] = mapped_column(String(100))

    chief_complaint: Mapped[str] = mapped_column(String(500))
    hpi: Mapped[str] = mapped_column(String(4000))
    family_history: Mapped[str] = mapped_column(String(2000), default="")
    surgical_history: Mapped[str] = mapped_column(String(2000), default="")
    social_history: Mapped[str] = mapped_column(String(2000), default="")

    # Nested chart / status payloads mirroring frontend types
    status: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    allergies: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    medications: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    problems: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    labs: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    vitals: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    encounter: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Snapshot used by practice-patient reset
    practice_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
