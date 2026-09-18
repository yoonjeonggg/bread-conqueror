"""store partnership management (F-ADMIN-06, roadmap phase 5)

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-17

- stores.is_partner / stores.partnered_at   제휴 매장 여부 · 제휴 시작일
- notifications.type ENUM 에 PARTNERSHIP_GRANTED / PARTNERSHIP_REVOKED 추가

0001 이 ``Base.metadata.create_all`` 기반이라 새 배포에서는 이 컬럼들이 이미
존재할 수 있으므로 리플렉션으로 확인 후 없을 때만 적용한다 (idempotent).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

_OLD_NOTIFICATION_TYPE = sa.Enum(
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
_NEW_NOTIFICATION_TYPE = sa.Enum(
    "FOLLOW",
    "POST_COMMENT",
    "POST_LIKE",
    "CLAIM_APPROVED",
    "CLAIM_REJECTED",
    "TIER_UP",
    "FLAG_APPROVED",
    "FLAG_INVALIDATED",
    "QR_CONQUEST",
    "PARTNERSHIP_GRANTED",
    "PARTNERSHIP_REVOKED",
    name="notificationtype",
)


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_column(table: str, column: str) -> bool:
    insp = _inspector()
    if not insp.has_table(table):
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    if not _has_column("stores", "is_partner"):
        op.add_column(
            "stores",
            sa.Column(
                "is_partner", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
        )
    if not _has_column("stores", "partnered_at"):
        op.add_column(
            "stores", sa.Column("partnered_at", sa.DateTime(), nullable=True)
        )

    insp = _inspector()
    notif_type = next(
        (c for c in insp.get_columns("notifications") if c["name"] == "type"),
        None,
    )
    if notif_type is not None and "PARTNERSHIP_GRANTED" not in str(
        notif_type["type"]
    ):
        op.alter_column(
            "notifications",
            "type",
            existing_type=_OLD_NOTIFICATION_TYPE,
            type_=_NEW_NOTIFICATION_TYPE,
            existing_nullable=False,
        )


def downgrade() -> None:
    insp = _inspector()
    notif_type = next(
        (c for c in insp.get_columns("notifications") if c["name"] == "type"),
        None,
    )
    if notif_type is not None and "PARTNERSHIP_GRANTED" in str(notif_type["type"]):
        op.alter_column(
            "notifications",
            "type",
            existing_type=_NEW_NOTIFICATION_TYPE,
            type_=_OLD_NOTIFICATION_TYPE,
            existing_nullable=False,
        )

    if _has_column("stores", "partnered_at"):
        op.drop_column("stores", "partnered_at")
    if _has_column("stores", "is_partner"):
        op.drop_column("stores", "is_partner")
