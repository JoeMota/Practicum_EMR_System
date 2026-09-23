"""Identity + RBAC (FR-01..FR-08). Roles, disciplines and permissions are
data-driven rows, not hard-coded enums, per the Week 0 design note."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Uuid, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Uuid, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Uuid, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Discipline(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "disciplines"

    code: Mapped[str] = mapped_column(String(50), unique=True)  # e.g. "nursing", "pt"
    name: Mapped[str] = mapped_column(String(100))


class Permission(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True)  # e.g. "patient:read"
    description: Mapped[str | None] = mapped_column(String(255))


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(50), unique=True)  # e.g. "instructor", "front_desk"
    name: Mapped[str] = mapped_column(String(100))

    permissions: Mapped[list[Permission]] = relationship(secondary=role_permissions)


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)  # FR-08
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    university_id: Mapped[str | None] = mapped_column(String(20))  # 800 number
    phone_last4: Mapped[str | None] = mapped_column(String(4))
    # Microsoft Entra object id when the account has signed in via UTEP SSO
    entra_oid: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)

    # Open client question #2 (multiple roles/disciplines?). Nullable single FK for now.
    discipline_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("disciplines.id"))

    discipline: Mapped[Discipline | None] = relationship()
    roles: Mapped[list[Role]] = relationship(secondary=user_roles)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
