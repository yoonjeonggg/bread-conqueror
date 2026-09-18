"""perf indexes: flags(user_id, created_at), follows(followee_id)

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-17

- flags 는 (user_id, store_id) / (store_id, type) 인덱스만 있어서, 정복/미션
  경로의 흔한 조회 패턴("user_id 로 좁힌 뒤 created_at 으로 정렬·범위 필터" —
  최근 깃발 조회, 실버 일일/쿨다운 체크)이 인덱스를 제대로 못 타고 있었다.
- follows 는 (follower_id, followee_id) 유니크 인덱스뿐이라, 팔로워 수 조회
  (`followee_id = ?`)는 그 인덱스의 왼쪽 접두사에 걸리지 않아 풀스캔이었다.

0001 이 create_all 기반이라 새 배포에서는 이미 존재할 수 있으므로 리플렉션으로
확인 후 없을 때만 만든다 (idempotent).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

_FLAGS_INDEX = "idx_flags_user_created"
_FOLLOWS_INDEX = "idx_follows_followee"


def _has_index(table: str, name: str) -> bool:
    insp = sa.inspect(op.get_bind())
    if not insp.has_table(table):
        return False
    return any(ix["name"] == name for ix in insp.get_indexes(table))


def upgrade() -> None:
    if not _has_index("flags", _FLAGS_INDEX):
        op.create_index(_FLAGS_INDEX, "flags", ["user_id", "created_at"])
    if not _has_index("follows", _FOLLOWS_INDEX):
        op.create_index(_FOLLOWS_INDEX, "follows", ["followee_id"])


def downgrade() -> None:
    if _has_index("follows", _FOLLOWS_INDEX):
        op.drop_index(_FOLLOWS_INDEX, table_name="follows")
    if _has_index("flags", _FLAGS_INDEX):
        op.drop_index(_FLAGS_INDEX, table_name="flags")
