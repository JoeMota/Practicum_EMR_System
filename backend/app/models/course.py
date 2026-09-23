"""Courses and enrollments — students find patients under their assigned class."""
import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Course(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "courses"

    code: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(200))
    term: Mapped[str] = mapped_column(String(50))
    rubric_file_name: Mapped[str | None] = mapped_column(String(255))

    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="course")


class Enrollment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One account across courses; each enrollment carries an app role + optional discipline."""

    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", "app_role", "discipline_code", name="uq_enrollment_slot"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    # Frontend Role: student | instructor | admin | front_desk | patient
    app_role: Mapped[str] = mapped_column(String(30))
    discipline_code: Mapped[str | None] = mapped_column(String(50))

    course: Mapped[Course] = relationship(back_populates="enrollments")
