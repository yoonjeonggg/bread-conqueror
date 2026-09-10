"""in-app notifications (roadmap phase 6)

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-10

notifications 테이블 하나를 추가한다. 0001 이 create_all 기반이라 새 배포에서는
이미 존재할 수 있으므로 리플렉션으로 확인 후 없을 때만 만든다 (idempotent).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_NOTIFICATION_TYPE = sa.Enum(
    "FOLLOW",
    "POST_COMMENT",
    "POST_LIKE",
    "CLAIM_APPROVED",
    "CLAIM_REJECTED",
    "TIER_UP",
    "FLAG_APPROVED",
    "FLAG_INVALIDATED",
    "QR_CONQUEST",
    name="notificationtype",
)


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if insp.has_table("notifications"):
        return

    op.create_table(
        "notifications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("recipient_id", sa.BigInteger(), nullable=False),
        sa.Column("actor_id", sa.BigInteger(), nullable=True),
        sa.Column("type", _NOTIFICATION_TYPE, nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=True),
        sa.Column("target_id", sa.BigInteger(), nullable=True),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column(
            "is_read", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_notifications_recipient",
        "notifications",
        ["recipient_id", "is_read", "created_at"],
    )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if insp.has_table("notifications"):
        op.drop_table("notifications")
