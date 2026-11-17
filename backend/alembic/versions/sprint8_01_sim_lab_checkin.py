"""Sim Center lab room catalog and student check-in assignments."""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "sprint8_01_sim_lab_checkin"
down_revision: Union[str, Sequence[str], None] = "sprint7_04_medication_orders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Schematic positions are relative (0–100). Storage / red-marked rooms omitted.
ROOMS = [
    # number, label, kind, beds, timing, sort, x, y, w, h
    ("126", "Lab 126", "big_lab", 10, "day", 10, 4, 4, 28, 22),
    ("127", "Lab 127", "ward", 5, "day", 20, 34, 4, 14, 18),
    ("120", "Lab 120", "ward", 5, "day", 30, 4, 72, 14, 22),
    ("111", "Lab 111", "ward", 5, "day", 40, 20, 72, 14, 22),
    ("109", "Lab 109", "ward", 5, "day", 50, 36, 72, 14, 22),
    ("105", "Lab 105", "ward", 5, "day", 60, 52, 72, 14, 22),
    ("104", "Lab 104", "ward", 5, "day", 70, 68, 72, 14, 22),
    ("103", "Lab 103", "ward", 5, "day", 80, 84, 72, 12, 22),
    ("106", "Testing 106", "testing", 1, "hour", 90, 52, 48, 10, 12),
    ("107", "Testing 107", "testing", 1, "hour", 100, 64, 48, 10, 12),
    ("108", "Testing 108", "testing", 1, "hour", 110, 76, 48, 10, 12),
    ("110", "Testing 110", "testing", 1, "hour", 120, 40, 48, 10, 12),
    ("112", "Exam 112", "exam", 1, "hour", 130, 22, 30, 10, 12),
    ("113", "Exam 113", "exam", 1, "hour", 140, 22, 44, 10, 12),
    ("115", "Exam 115", "exam", 1, "hour", 150, 22, 58, 10, 12),
    ("116", "Exam 116", "exam", 1, "hour", 160, 22, 72, 10, 12),
]


def upgrade() -> None:
    op.create_table(
        "sim_lab_rooms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("bed_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("timing", sa.String(length=20), server_default="day", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("map_x", sa.Integer(), server_default="0", nullable=False),
        sa.Column("map_y", sa.Integer(), server_default="0", nullable=False),
        sa.Column("map_w", sa.Integer(), server_default="10", nullable=False),
        sa.Column("map_h", sa.Integer(), server_default="10", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("number"),
    )
    op.create_table(
        "sim_lab_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("room_id", sa.Uuid(), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("bed", sa.String(length=8), nullable=True),
        sa.Column("role_label", sa.String(length=40), nullable=True),
        sa.Column("time_block", sa.String(length=40), nullable=True),
        sa.Column("assigned_by_id", sa.Uuid(), nullable=False),
        sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["assigned_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_id"], ["sim_lab_rooms.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sim_lab_assignments_course_id", "sim_lab_assignments", ["course_id"])
    op.create_index("ix_sim_lab_assignments_user_id", "sim_lab_assignments", ["user_id"])
    op.create_index("ix_sim_lab_assignments_room_id", "sim_lab_assignments", ["room_id"])
    op.create_index("ix_sim_lab_assignments_session_date", "sim_lab_assignments", ["session_date"])

    rooms = sa.table(
        "sim_lab_rooms",
        sa.column("id", sa.Uuid()),
        sa.column("number", sa.String()),
        sa.column("label", sa.String()),
        sa.column("kind", sa.String()),
        sa.column("bed_count", sa.Integer()),
        sa.column("timing", sa.String()),
        sa.column("sort_order", sa.Integer()),
        sa.column("map_x", sa.Integer()),
        sa.column("map_y", sa.Integer()),
        sa.column("map_w", sa.Integer()),
        sa.column("map_h", sa.Integer()),
    )
    import uuid

    op.bulk_insert(
        rooms,
        [
            {
                "id": uuid.uuid4(),
                "number": number,
                "label": label,
                "kind": kind,
                "bed_count": beds,
                "timing": timing,
                "sort_order": sort,
                "map_x": x,
                "map_y": y,
                "map_w": w,
                "map_h": h,
            }
            for number, label, kind, beds, timing, sort, x, y, w, h in ROOMS
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_sim_lab_assignments_session_date", table_name="sim_lab_assignments")
    op.drop_index("ix_sim_lab_assignments_room_id", table_name="sim_lab_assignments")
    op.drop_index("ix_sim_lab_assignments_user_id", table_name="sim_lab_assignments")
    op.drop_index("ix_sim_lab_assignments_course_id", table_name="sim_lab_assignments")
    op.drop_table("sim_lab_assignments")
    op.drop_table("sim_lab_rooms")
