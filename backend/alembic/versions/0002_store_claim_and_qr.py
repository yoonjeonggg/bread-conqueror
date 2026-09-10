"""store ownership claims + conquest QR tokens (roadmap phase 5)

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-10

- stores.owner_id            인증된 소유자
- store_claims.review_note   반려/승인 사유 (사용자에게 노출)
- store_qr_tokens            매장 QR 정복 토큰
- flags.evidence_type        ENUM 에 'QR' 추가

주의: 0001 은 ``Base.metadata.create_all`` 로 스키마를 통째로 만든다. 따라서
새 배포에서는 여기서 추가하는 컬럼/테이블이 0001 시점에 이미 존재할 수 있고,
반대로 기존 배포에서는 없다. 두 경우 모두를 위해 각 단계는 리플렉션으로
현재 상태를 확인한 뒤 필요한 것만 적용한다 (idempotent).
"""

from __future__ import annotations

import contextlib

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_OLD_EVIDENCE = sa.Enum("NONE", "PHOTO", "RECEIPT", "REALTIME_GPS", name="evidencetype")
_NEW_EVIDENCE = sa.Enum(
    "NONE", "PHOTO", "RECEIPT", "REALTIME_GPS", "QR", name="evidencetype"
)


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_column(table: str, column: str) -> bool:
    insp = _inspector()
    if not insp.has_table(table):
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    insp = _inspector()

    if not _has_column("stores", "owner_id"):
        op.add_column("stores", sa.Column("owner_id", sa.BigInteger(), nullable=True))
        op.create_foreign_key(
            "fk_stores_owner_id_users", "stores", "users", ["owner_id"], ["id"]
        )

    if not _has_column("store_claims", "review_note"):
        op.add_column(
            "store_claims",
            sa.Column("review_note", sa.String(length=255), nullable=True),
        )

    if not insp.has_table("store_qr_tokens"):
        op.create_table(
            "store_qr_tokens",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("store_id", sa.BigInteger(), nullable=False),
            sa.Column("token", sa.String(length=64), nullable=False),
            sa.Column("created_by", sa.BigInteger(), nullable=False),
            sa.Column("label", sa.String(length=50), nullable=True),
            sa.Column("max_uses", sa.Integer(), nullable=True),
            sa.Column(
                "use_count", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_store_qr_tokens_token", "store_qr_tokens", ["token"], unique=True
        )

    # ENUM 에 'QR' 이 이미 포함돼 있지 않을 때만 MODIFY
    evidence_type = next(
        (c for c in insp.get_columns("flags") if c["name"] == "evidence_type"),
        None,
    )
    if evidence_type is not None and "QR" not in str(evidence_type["type"]):
        op.alter_column(
            "flags",
            "evidence_type",
            existing_type=_OLD_EVIDENCE,
            type_=_NEW_EVIDENCE,
            existing_nullable=False,
        )


def downgrade() -> None:
    insp = _inspector()

    evidence_type = next(
        (c for c in insp.get_columns("flags") if c["name"] == "evidence_type"),
        None,
    )
    if evidence_type is not None and "QR" in str(evidence_type["type"]):
        op.alter_column(
            "flags",
            "evidence_type",
            existing_type=_NEW_EVIDENCE,
            type_=_OLD_EVIDENCE,
            existing_nullable=False,
        )

    if insp.has_table("store_qr_tokens"):
        op.drop_table("store_qr_tokens")
    if _has_column("store_claims", "review_note"):
        op.drop_column("store_claims", "review_note")
    if _has_column("stores", "owner_id"):
        # FK 이름이 환경마다 다를 수 있으므로 실패는 무시
        with contextlib.suppress(Exception):
            op.drop_constraint(
                "fk_stores_owner_id_users", "stores", type_="foreignkey"
            )
        op.drop_column("stores", "owner_id")
