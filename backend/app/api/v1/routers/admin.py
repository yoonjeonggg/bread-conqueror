"""관리자 기능 (F-ADMIN). RBAC-gated. Phase 4.

Implemented: flag review queue + invalidation, basic stats dashboard.
Stubbed for later: store merge (F-ADMIN-04), bulk upload (F-ADMIN-05),
user suspension (F-ADMIN-07), content moderation (F-ADMIN-09).
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.core.dependencies import CurrentAdmin, DbSession
from app.models.enums import FlagStatus, FlagType
from app.models.flag import Flag
from app.models.policy import AdminActionLog
from app.models.store import Store
from app.models.user import User
from app.schemas.flag import FlagOut

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[])


@router.get("/flags/review-queue", response_model=list[FlagOut])
async def review_queue(db: DbSession, admin: CurrentAdmin) -> list[Flag]:
    """F-ADMIN-01/02 — auto-flagged or reported conquests awaiting review."""
    return list(
        (
            await db.execute(
                select(Flag)
                .where(
                    (Flag.is_flagged.is_(True))
                    | (Flag.status == FlagStatus.UNDER_REVIEW)
                )
                .order_by(Flag.created_at.desc())
                .limit(200)
            )
        )
        .scalars()
        .all()
    )


@router.post("/flags/{flag_id}/invalidate", response_model=FlagOut)
async def invalidate_flag(
    flag_id: int, db: DbSession, admin: CurrentAdmin
) -> Flag:
    flag = await db.get(Flag, flag_id)
    if flag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    flag.status = FlagStatus.INVALIDATED
    db.add(
        AdminActionLog(
            admin_id=admin.id,
            action_type="FLAG_INVALIDATE",
            target_type="FLAG",
            target_id=flag_id,
        )
    )
    await db.commit()
    await db.refresh(flag)
    return flag


@router.post("/flags/{flag_id}/approve", response_model=FlagOut)
async def approve_flag(flag_id: int, db: DbSession, admin: CurrentAdmin) -> Flag:
    flag = await db.get(Flag, flag_id)
    if flag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    flag.status = FlagStatus.VALID
    flag.is_flagged = False
    db.add(
        AdminActionLog(
            admin_id=admin.id,
            action_type="FLAG_APPROVE",
            target_type="FLAG",
            target_id=flag_id,
        )
    )
    await db.commit()
    await db.refresh(flag)
    return flag


@router.get("/stats/dashboard")
async def dashboard(db: DbSession, admin: CurrentAdmin) -> dict:
    """F-ADMIN-10 — headline metrics."""
    week_ago = datetime.utcnow() - timedelta(days=7)

    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    total_stores = (
        await db.execute(select(func.count()).select_from(Store))
    ).scalar_one()
    total_flags = (
        await db.execute(select(func.count()).select_from(Flag))
    ).scalar_one()
    gold = (
        await db.execute(
            select(func.count()).select_from(Flag).where(Flag.type == FlagType.GOLD)
        )
    ).scalar_one()
    flags_this_week = (
        await db.execute(
            select(func.count())
            .select_from(Flag)
            .where(Flag.created_at >= week_ago)
        )
    ).scalar_one()
    pending_review = (
        await db.execute(
            select(func.count())
            .select_from(Flag)
            .where(Flag.is_flagged.is_(True))
        )
    ).scalar_one()

    return {
        "total_users": total_users,
        "total_stores": total_stores,
        "total_flags": total_flags,
        "gold_ratio": round(gold / total_flags, 3) if total_flags else 0.0,
        "flags_this_week": flags_this_week,
        "pending_review": pending_review,
    }
