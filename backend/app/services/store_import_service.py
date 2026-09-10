"""매장 CSV 대량 등록 (F-ADMIN-05).

헤더 있는 CSV 텍스트를 받아 행마다 검증 → 반경 30m 중복 스킵 → 매장 생성.
`dry_run` 이면 생성하지 않고 결과만 돌려준다. 라우터가 커밋을 소유한다.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import StoreCreatedSource, StoreStatus
from app.models.store import Store, StoreStat
from app.services.geo_service import haversine_m

DEDUP_RADIUS_M = 30.0
REQUIRED_COLUMNS = ("name", "address", "lat", "lng")
MAX_ROWS = 1000


@dataclass
class RowResult:
    line: int
    name: str
    status: str  # created | skipped | failed
    detail: str | None = None
    store_id: int | None = None


@dataclass
class ImportResult:
    dry_run: bool
    total: int = 0
    created: int = 0
    skipped_duplicate: int = 0
    failed: int = 0
    rows: list[RowResult] = field(default_factory=list)


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _optional(row: dict[str, str], key: str, limit: int) -> str | None:
    val = row.get(key, "")
    return val[:limit] if val else None


async def import_stores(
    db: AsyncSession, *, csv_text: str, dry_run: bool
) -> ImportResult:
    reader = csv.DictReader(io.StringIO(csv_text))
    header = {_clean(f) for f in (reader.fieldnames or [])}
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV 헤더에 필수 컬럼이 없습니다: {', '.join(missing)}",
        )

    result = ImportResult(dry_run=dry_run)

    existing: list[tuple[float, float]] = [
        (float(lat), float(lng))
        for lat, lng in (await db.execute(select(Store.lat, Store.lng))).all()
    ]
    batch: list[tuple[float, float]] = []

    for line, raw in enumerate(reader, start=2):  # 헤더가 1행
        if result.total >= MAX_ROWS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"한 번에 최대 {MAX_ROWS}행까지 처리할 수 있습니다.",
            )
        row = {_clean(k): _clean(v) for k, v in raw.items()}
        name = row.get("name", "")
        result.total += 1

        try:
            if not name:
                raise ValueError("name 이 비어 있습니다.")
            if not row.get("address"):
                raise ValueError("address 가 비어 있습니다.")
            lat = float(row["lat"])
            lng = float(row["lng"])
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                raise ValueError("좌표 범위를 벗어났습니다.")
        except (ValueError, KeyError) as exc:
            result.failed += 1
            result.rows.append(
                RowResult(line, name or "(빈 이름)", "failed", str(exc))
            )
            continue

        near = any(
            haversine_m(lat, lng, elat, elng) <= DEDUP_RADIUS_M
            for elat, elng in existing
        ) or any(
            haversine_m(lat, lng, blat, blng) <= DEDUP_RADIUS_M
            for blat, blng in batch
        )
        if near:
            result.skipped_duplicate += 1
            result.rows.append(
                RowResult(line, name, "skipped", "반경 30m 내 기존/직전 매장과 중복")
            )
            continue

        batch.append((lat, lng))
        result.created += 1

        if dry_run:
            result.rows.append(RowResult(line, name, "created", "dry-run"))
            continue

        store = Store(
            name=name[:100],
            address=row["address"][:255],
            region_sido=_optional(row, "region_sido", 50),
            lat=Decimal(str(lat)),
            lng=Decimal(str(lng)),
            category=_optional(row, "category", 50),
            created_source=StoreCreatedSource.AUTO_COLLECTED,
            status=StoreStatus.ACTIVE,
        )
        store.stat = StoreStat()
        db.add(store)
        await db.flush()
        result.rows.append(RowResult(line, name, "created", None, store.id))

    return result
