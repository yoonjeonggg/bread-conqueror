"""Seed reference data + a demo dataset.

Usage (from backend/):  python -m scripts.seed
"""

from __future__ import annotations

import asyncio
import secrets
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.enums import (
    MissionMetric,
    StoreCreatedSource,
    StoreStatus,
    UserRole,
)
from app.models.mission import MissionDefinition
from app.models.policy import PolicyConfig, TierPolicy
from app.models.store import Store, StoreStat
from app.models.store_qr_token import StoreQrToken
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

# (code, title, description, metric, target, reward_exp, sort_order)
MISSIONS = [
    ("WEEKLY_GOLD_3", "골드 사냥꾼", "이번 주에 골드 깃발 3개 꽂기",
     MissionMetric.GOLD_FLAGS, 3, 150, 10),
    ("WEEKLY_ANY_5", "부지런한 빵순이", "이번 주에 깃발 5개 꽂기",
     MissionMetric.TOTAL_FLAGS, 5, 100, 20),
    ("WEEKLY_REVIEW_2", "리뷰어", "이번 주에 리뷰 2개 남기기",
     MissionMetric.REVIEWS, 2, 80, 30),
    ("WEEKLY_EXPLORE_3", "탐험가", "이번 주에 서로 다른 빵집 3곳 정복",
     MissionMetric.DISTINCT_STORES, 3, 120, 40),
    ("WEEKLY_REGION_2", "원정대", "이번 주에 2개 이상 지역에서 정복",
     MissionMetric.DISTINCT_REGIONS, 2, 200, 50),
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

        for code, title, desc, metric, target, reward, order in MISSIONS:
            if await db.get(MissionDefinition, code) is None:
                db.add(
                    MissionDefinition(
                        code=code,
                        title=title,
                        description=desc,
                        metric=metric,
                        target=target,
                        reward_exp=reward,
                        sort_order=order,
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

        await db.flush()

        # 데모: demo 계정을 '밀도 성수' 인증 소유자로 연결하고 정복용 QR 토큰 발급
        demo_user = (
            await db.execute(select(User).where(User.email == "demo@bread.dev"))
        ).scalar_one_or_none()
        mildo = (
            await db.execute(select(Store).where(Store.name == "밀도 성수"))
        ).scalar_one_or_none()
        if demo_user is not None and mildo is not None and mildo.owner_id is None:
            mildo.owner_id = demo_user.id
            mildo.is_verified_owner = True
            db.add(
                StoreQrToken(
                    store_id=mildo.id,
                    token=secrets.token_urlsafe(24),
                    created_by=demo_user.id,
                    label="데모 카운터 QR",
                )
            )

        await db.commit()
    print("seed complete: policies, tiers, admin@bread.dev / demo@bread.dev, demo stores")


if __name__ == "__main__":
    asyncio.run(seed())
