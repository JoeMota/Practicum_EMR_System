"""Clinical notes + review workflow (FR-18..FR-20). Soft-delete / archive only."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ClinicalNote(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "clinical_notes"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    encounter_id: Mapped[str] = mapped_column(String(80))
    template_id: Mapped[str] = mapped_column(String(50))
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    author_name: Mapped[str] = mapped_column(String(200))
    author_discipline: Mapped[str] = mapped_column(String(50))
    mode: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    content: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    diagnoses: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    feedback: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    addenda: Mapped[list[Any]] = mapped_column(JSONB, default=list)

    routed_to_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cosigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cosigned_by_name: Mapped[str | None] = mapped_column(String(200))

    # When practice patients are reset, notes move here instead of hard delete
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
