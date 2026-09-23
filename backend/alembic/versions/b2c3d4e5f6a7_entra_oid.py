"""Link users to Microsoft Entra OID for UTEP SSO

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("entra_oid", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_users_entra_oid"), "users", ["entra_oid"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_entra_oid"), table_name="users")
    op.drop_column("users", "entra_oid")
