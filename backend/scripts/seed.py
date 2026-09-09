"""Seed reference data + a demo dataset.

Usage (from backend/):  python -m scripts.seed
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.enums import StoreCreatedSource, StoreStatus, UserRole
from app.models.policy import PolicyConfig, TierPolicy
from app.models.store import Store, StoreStat
from app.models.user import User, UserStat

POLICY_CONFIGS = [
    ("CONQUEST_RADIUS_M", "50", "실시간 인증 GPS 반경(m)"),
    ("COOLDOWN_HOURS", "24", "동일 매장 재인증 쿨다운(시간)"),
    ("SILVER_DAILY_LIMIT", "5", "실버 깃발 일일 등록 제한(건)"),
    ("SILVER_TOTAL_LIMIT", "30", "실버 깃발 누적 등록 제한(건)"),
    ("TIER4_GOLD_RATIO", "0.70", "전국 정복자 이상 골드 비율 요건"),
    ("GOLD_EXP", "100", "골드 깃발 경험치"),
    ("SILVER_EXP_RATIO", "0.5", "실버 깃발 경험치 비율"),
    ("ABUSE_SPEED_KMH", "150", "이상 탐지 이동 속도 임계값(km/h)"),
]

TIER_POLICIES = [
    (1, "빵 입문자", 0, None),
    (2, "빵 탐험가", 300, None),
    (3, "지역 정복자", 1200, None),
    (4, "전국 정복자", 4000, Decimal("0.70")),
    (5, "전설의 빵 정복자", 12000, Decimal("0.70")),
]

# A few real-ish Seoul bakeries for the map demo.
DEMO_STORES = [
    ("김진환제과점", "서울 중구 세종대로 39", "서울", 37.5642, 126.9770, "베이커리"),
    ("아우어베이커리 도산", "서울 강남구 압구정로46길 50", "서울", 37.5254, 127.0389, "베이커리"),
    ("르알래스카", "서울 용산구 신흥로 95", "서울", 37.5405, 126.9880, "베이커리"),
    ("나폴레옹과자점 본점", "서울 성북구 동소문로 20길 33", "서울", 37.5894, 127.0163, "베이커리"),
    ("폴앤폴리나", "서울 마포구 성미산로 156", "서울", 37.5645, 126.9270, "베이커리"),
    ("밀도 성수", "서울 성동구 아차산로 15", "서울", 37.5449, 127.0561, "베이커리"),
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        for key, value, desc in POLICY_CONFIGS:
            if await db.get(PolicyConfig, key) is None:
                db.add(
                    PolicyConfig(config_key=key, config_value=value, description=desc)
                )

        for level, name, exp, ratio in TIER_POLICIES:
            if await db.get(TierPolicy, level) is None:
                db.add(
                    TierPolicy(
                        tier_level=level,
                        tier_name=name,
                        required_exp=exp,
                        gold_ratio_requirement=ratio,
                    )
                )

        existing = (
            await db.execute(select(User).where(User.email == "admin@bread.dev"))
        ).scalar_one_or_none()
        if existing is None:
            admin = User(
                nickname="빵관리자",
                email="admin@bread.dev",
                password_hash=hash_password("admin1234"),
                role=UserRole.ADMIN,
            )
            admin.stat = UserStat()
            db.add(admin)

            demo = User(
                nickname="빵순이",
                email="demo@bread.dev",
                password_hash=hash_password("demo1234"),
            )
            demo.stat = UserStat()
            db.add(demo)

        has_stores = (
            await db.execute(select(Store.id).limit(1))
        ).scalar_one_or_none()
        if has_stores is None:
            for name, address, sido, lat, lng, category in DEMO_STORES:
                store = Store(
                    name=name,
                    address=address,
                    region_sido=sido,
                    lat=Decimal(str(lat)),
                    lng=Decimal(str(lng)),
                    category=category,
                    created_source=StoreCreatedSource.AUTO_COLLECTED,
                    status=StoreStatus.ACTIVE,
                )
                store.stat = StoreStat()
                db.add(store)

        await db.commit()
    print("seed complete: policies, tiers, admin@bread.dev / demo@bread.dev, demo stores")


if __name__ == "__main__":
    asyncio.run(seed())
