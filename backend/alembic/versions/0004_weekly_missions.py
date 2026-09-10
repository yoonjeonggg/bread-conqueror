"""weekly missions (roadmap phase 8)

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-10

mission_definitions (참조 데이터) + mission_claims (보상 수령 기록).
0001 이 create_all 기반이라 새 배포에서는 이미 존재할 수 있으므로 리플렉션으로
확인 후 없을 때만 만든다 (idempotent).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

_METRIC = sa.Enum(
    "GOLD_FLAGS",
    "SILVER_FLAGS",
    "TOTAL_FLAGS",
    "REVIEWS",
    "DISTINCT_STORES",
    "DISTINCT_REGIONS",
    name="missionmetric",
)


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())

    if not insp.has_table("mission_definitions"):
        op.create_table(
            "mission_definitions",
            sa.Column("code", sa.String(length=40), nullable=False),
            sa.Column("title", sa.String(length=80), nullable=False),
            sa.Column("description", sa.String(length=200), nullable=False),
            sa.Column("metric", _METRIC, nullable=False),
            sa.Column("target", sa.Integer(), nullable=False),
            sa.Column("reward_exp", sa.Integer(), nullable=False),
            sa.Column(
                "sort_order", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column(
                "active", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
            sa.PrimaryKeyConstraint("code"),
        )

    if not insp.has_table("mission_claims"):
        op.create_table(
            "mission_claims",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("mission_code", sa.String(length=40), nullable=False),
            sa.Column("week_start", sa.Date(), nullable=False),
            sa.Column("reward_exp", sa.Integer(), nullable=False),
            sa.Column(
                "claimed_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id",
                "mission_code",
                "week_start",
                name="uq_mission_claims_user_mission_week",
            ),
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if insp.has_table("mission_claims"):
        op.drop_table("mission_claims")
    if insp.has_table("mission_definitions"):
        op.drop_table("mission_definitions")
