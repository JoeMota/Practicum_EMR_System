"""Appointments and referrals (FR-23, FR-28) — basic outpatient support."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class Appointment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "appointments"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    when: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    kind: Mapped[str] = mapped_column(String(200))
    with_whom: Mapped[str] = mapped_column(String(200))


class Referral(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "referrals"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    to_discipline: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str] = mapped_column(String(1000))
    urgency: Mapped[str] = mapped_column(String(20), default="routine")
    created_by_name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
