"""Protected notes, refresh tokens, and login lockout."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "sprint4_01_access"
down_revision: Union[str, Sequence[str], None] = "sprint3_14_templates_photo"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("failed_login_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "clinical_notes",
        sa.Column("sensitivity", sa.String(length=20), server_default="standard", nullable=False),
    )
    op.add_column("clinical_notes", sa.Column("content_cipher", sa.Text(), nullable=True))
    op.add_column("note_comments", sa.Column("body_cipher", sa.Text(), nullable=True))
    op.add_column("note_addenda", sa.Column("body_cipher", sa.Text(), nullable=True))
    op.add_column(
        "note_templates",
        sa.Column("sensitivity", sa.String(length=20), server_default="standard", nullable=False),
    )
    op.execute("UPDATE clinical_notes SET sensitivity = 'protected' WHERE sensitive = true")
    op.execute("UPDATE note_templates SET sensitivity = 'protected' WHERE sensitive = true")
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_column("note_templates", "sensitivity")
    op.drop_column("note_addenda", "body_cipher")
    op.drop_column("note_comments", "body_cipher")
    op.drop_column("clinical_notes", "content_cipher")
    op.drop_column("clinical_notes", "sensitivity")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_count")
