"""관리자 기능 (F-ADMIN). RBAC-gated.

- F-ADMIN-01/02  깃발 검토 큐 · 승인/무효화 · 이상탐지 목록
- F-ADMIN-07     계정 정지 / 해제
- F-ADMIN-08     경험치·티어 수동 조정
- F-ADMIN-09     신고 처리 · 게시글/댓글 모더레이션
- F-ADMIN-10     통계 대시보드

아직 스텁: 매장 병합(F-ADMIN-04), 엑셀 대량 업로드(F-ADMIN-05).
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentAdmin, DbSession
from app.models.enums import (
    ClaimStatus,
    FlagStatus,
    FlagType,
    ReportStatus,
    UserStatus,
)
from app.models.flag import Flag
from app.models.policy import AdminActionLog
from app.models.post import Comment, Post
from app.models.social import Report
from app.models.store import Store, StoreStat
from app.models.store_claim import StoreClaim
from app.models.user import User, UserStat
from app.schemas.admin import (
    AdjustExpRequest,
    AdjustResultOut,
    AdminReportOut,
    AdminUserOut,
    DashboardOut,
    ModerateRequest,
    ResolveReportRequest,
    SuspendRequest,
)
from app.schemas.claim import AdminClaimOut, ClaimOut, ClaimReviewRequest
from app.schemas.flag import FlagOut
from app.services import tier_service

router = APIRouter(prefix="/admin", tags=["admin"])


def _log(
    db: AsyncSession,
    admin_id: int,
    action_type: str,
    target_type: str,
    target_id: int,
    detail: str | None = None,
) -> None:
    db.add(
        AdminActionLog(
            admin_id=admin_id,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
    )


# --- 깃발 (F-ADMIN-01/02) -------------------------------------------------


@router.get("/flags/review-queue", response_model=list[FlagOut])
async def review_queue(db: DbSession, admin: CurrentAdmin) -> list[Flag]:
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
async def invalidate_flag(flag_id: int, db: DbSession, admin: CurrentAdmin) -> Flag:
    flag = await db.get(Flag, flag_id)
    if flag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    flag.status = FlagStatus.INVALIDATED
    _log(db, admin.id, "FLAG_INVALIDATE", "FLAG", flag_id)
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
    _log(db, admin.id, "FLAG_APPROVE", "FLAG", flag_id)
    await db.commit()
    await db.refresh(flag)
    return flag


# --- 계정 관리 (F-ADMIN-07/08) ------------------------------------------


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(db: DbSession, admin: CurrentAdmin) -> list[User]:
    return list(
        (await db.execute(select(User).order_by(User.created_at.desc()).limit(200)))
        .scalars()
        .all()
    )


@router.post("/users/{user_id}/suspend", response_model=AdminUserOut)
async def suspend_user(
    user_id: int, payload: SuspendRequest, db: DbSession, admin: CurrentAdmin
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user.status = UserStatus.SUSPENDED
    _log(db, admin.id, "USER_SUSPEND", "USER", user_id, payload.reason)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/users/{user_id}/reactivate", response_model=AdminUserOut)
async def reactivate_user(
    user_id: int, db: DbSession, admin: CurrentAdmin
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user.status = UserStatus.ACTIVE
    _log(db, admin.id, "USER_REACTIVATE", "USER", user_id)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/users/{user_id}/adjust-exp", response_model=AdjustResultOut)
async def adjust_exp(
    user_id: int, payload: AdjustExpRequest, db: DbSession, admin: CurrentAdmin
) -> AdjustResultOut:
    stat = await db.get(UserStat, user_id)
    if stat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    stat.exp = max(0, stat.exp + payload.exp_delta)
    tier_changed = await tier_service.recalculate_tier(db, stat)
    _log(
        db,
        admin.id,
        "USER_ADJUST_EXP",
        "USER",
        user_id,
        f"delta={payload.exp_delta}; {payload.reason}",
    )
    await db.commit()
    return AdjustResultOut(
        user_id=user_id,
        exp=stat.exp,
        tier_level=stat.tier_level,
        tier_changed=tier_changed,
    )


# --- 신고 · 모더레이션 (F-ADMIN-09) -----------------------------------


@router.get("/reports", response_model=list[AdminReportOut])
async def list_reports(
    db: DbSession,
    admin: CurrentAdmin,
    only_pending: bool = True,
) -> list[Report]:
    stmt = select(Report).order_by(Report.created_at.desc()).limit(200)
    if only_pending:
        stmt = stmt.where(Report.status == ReportStatus.PENDING)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/reports/{report_id}/resolve", response_model=AdminReportOut)
async def resolve_report(
    report_id: int,
    payload: ResolveReportRequest,
    db: DbSession,
    admin: CurrentAdmin,
) -> Report:
    report = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    report.status = payload.status
    _log(db, admin.id, "REPORT_RESOLVE", "REPORT", report_id, payload.note)
    await db.commit()
    await db.refresh(report)
    return report


@router.post("/posts/{post_id}/moderate")
async def moderate_post(
    post_id: int, payload: ModerateRequest, db: DbSession, admin: CurrentAdmin
) -> dict:
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    post.status = payload.status
    _log(db, admin.id, "POST_MODERATE", "POST", post_id, payload.reason)
    await db.commit()
    return {"post_id": post_id, "status": payload.status}


@router.post("/comments/{comment_id}/moderate")
async def moderate_comment(
    comment_id: int, payload: ModerateRequest, db: DbSession, admin: CurrentAdmin
) -> dict:
    comment = await db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    comment.status = payload.status
    _log(db, admin.id, "COMMENT_MODERATE", "COMMENT", comment_id, payload.reason)
    await db.commit()
    return {"comment_id": comment_id, "status": payload.status}


# --- 매장 소유권 신청 (로드맵 5단계) --------------------------------


@router.get("/claims", response_model=list[AdminClaimOut])
async def list_claims(
    db: DbSession, admin: CurrentAdmin, only_pending: bool = True
) -> list[AdminClaimOut]:
    stmt = (
        select(StoreClaim, Store.name, User.nickname)
        .join(Store, Store.id == StoreClaim.store_id)
        .join(User, User.id == StoreClaim.user_id)
        .order_by(StoreClaim.created_at.desc())
        .limit(200)
    )
    if only_pending:
        stmt = stmt.where(StoreClaim.status == ClaimStatus.PENDING)
    rows = (await db.execute(stmt)).all()
    return [
        AdminClaimOut.model_validate(
            {**claim.__dict__, "store_name": store_name, "user_nickname": nickname}
        )
        for claim, store_name, nickname in rows
    ]


async def _decide_claim(
    db: AsyncSession,
    admin: User,
    claim_id: int,
    approve: bool,
    note: str | None,
) -> StoreClaim:
    claim = await db.get(StoreClaim, claim_id)
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if claim.status is not ClaimStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="이미 처리된 신청입니다."
        )

    now = datetime.utcnow()
    claim.reviewed_by = admin.id
    claim.reviewed_at = now
    claim.review_note = note

    if approve:
        store = await db.get(Store, claim.store_id)
        if store is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        if store.owner_id is not None and store.owner_id != claim.user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 다른 소유자가 인증된 매장입니다.",
            )
        claim.status = ClaimStatus.APPROVED
        store.owner_id = claim.user_id
        store.is_verified_owner = True

        # 같은 매장의 다른 대기 신청은 자동 반려
        others = (
            (
                await db.execute(
                    select(StoreClaim).where(
                        StoreClaim.store_id == claim.store_id,
                        StoreClaim.id != claim.id,
                        StoreClaim.status == ClaimStatus.PENDING,
                    )
                )
            )
            .scalars()
            .all()
        )
        for other in others:
            other.status = ClaimStatus.REJECTED
            other.reviewed_by = admin.id
            other.reviewed_at = now
            other.review_note = "다른 신청이 승인되었습니다."
    else:
        claim.status = ClaimStatus.REJECTED

    _log(
        db,
        admin.id,
        "CLAIM_APPROVE" if approve else "CLAIM_REJECT",
        "STORE_CLAIM",
        claim_id,
        note,
    )
    await db.commit()
    await db.refresh(claim)
    return claim


@router.post("/claims/{claim_id}/approve", response_model=ClaimOut)
async def approve_claim(
    claim_id: int,
    payload: ClaimReviewRequest,
    db: DbSession,
    admin: CurrentAdmin,
) -> StoreClaim:
    return await _decide_claim(db, admin, claim_id, approve=True, note=payload.note)


@router.post("/claims/{claim_id}/reject", response_model=ClaimOut)
async def reject_claim(
    claim_id: int,
    payload: ClaimReviewRequest,
    db: DbSession,
    admin: CurrentAdmin,
) -> StoreClaim:
    return await _decide_claim(db, admin, claim_id, approve=False, note=payload.note)


# --- 대시보드 (F-ADMIN-10) --------------------------------------------


@router.get("/stats/dashboard", response_model=DashboardOut)
async def dashboard(db: DbSession, admin: CurrentAdmin) -> DashboardOut:
    week_ago = datetime.utcnow() - timedelta(days=7)

    async def count(model, *where) -> int:
        stmt = select(func.count()).select_from(model)
        for w in where:
            stmt = stmt.where(w)
        return (await db.execute(stmt)).scalar_one()

    total_flags = await count(Flag)
    gold = await count(Flag, Flag.type == FlagType.GOLD)
    avg_rating = (
        await db.execute(select(func.avg(StoreStat.average_rating)))
    ).scalar_one_or_none()

    return DashboardOut(
        total_users=await count(User),
        total_stores=await count(Store),
        total_flags=total_flags,
        gold_ratio=round(gold / total_flags, 3) if total_flags else 0.0,
        flags_this_week=await count(Flag, Flag.created_at >= week_ago),
        pending_review=await count(Flag, Flag.is_flagged.is_(True)),
        pending_reports=await count(Report, Report.status == ReportStatus.PENDING),
        pending_claims=await count(
            StoreClaim, StoreClaim.status == ClaimStatus.PENDING
        ),
        suspended_users=await count(User, User.status == UserStatus.SUSPENDED),
        average_store_rating=round(avg_rating, 2) if avg_rating is not None else None,
    )
