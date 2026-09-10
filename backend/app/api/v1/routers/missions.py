"""주간 미션 조회 / 보상 수령 (로드맵 8단계)."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import CurrentUser, DbSession
from app.core.redis import redis_client
from app.models.enums import NotificationType
from app.models.user import UserStat
from app.schemas.mission import ClaimResultOut, WeeklyMissionsOut
from app.services import mission_service, notification_service, ranking_service

router = APIRouter(prefix="/missions", tags=["missions"])


@router.get("/weekly", response_model=WeeklyMissionsOut)
async def weekly(db: DbSession, me: CurrentUser) -> WeeklyMissionsOut:
    week, missions = await mission_service.weekly_missions(db, me.id)
    return WeeklyMissionsOut(week_start=week, missions=missions)


@router.post("/{code}/claim", response_model=ClaimResultOut)
async def claim_mission(
    code: str, db: DbSession, me: CurrentUser
) -> ClaimResultOut:
    result = await mission_service.claim(db, user=me, mission_code=code)

    if result.tier_changed:
        await notification_service.create(
            db,
            recipient_id=me.id,
            type=NotificationType.TIER_UP,
            message=f"주간 미션 보상으로 티어가 Lv.{result.tier_level}(으)로 올랐습니다!",
            target_type="USER",
            target_id=me.id,
        )

    try:
        await db.commit()
    except IntegrityError as exc:  # 동시 클릭 등으로 중복 수령
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이번 주 보상을 이미 받았습니다.",
        ) from exc

    stat = await db.get(UserStat, me.id)
    if stat is not None:
        await ranking_service.set_score(redis_client, me.id, stat.exp)

    return ClaimResultOut.model_validate(result)
