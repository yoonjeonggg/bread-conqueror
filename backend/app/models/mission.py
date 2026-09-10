from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, BigIntPK
from app.models.enums import MissionMetric


class MissionDefinition(Base):
    """주간 미션 정의 (참조 데이터, seed 로 주입).

    진행도는 저장하지 않고 조회 시점에 flags/reviews 에서 계산한다.
    """

    __tablename__ = "mission_definitions"

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    metric: Mapped[MissionMetric] = mapped_column(
        Enum(MissionMetric), nullable=False
    )
    target: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_exp: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class MissionClaim(Base):
    """주간 미션 보상 수령 기록. (user, mission, week_start) 당 1회."""

    __tablename__ = "mission_claims"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "mission_code",
            "week_start",
            name="uq_mission_claims_user_mission_week",
        ),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    mission_code: Mapped[str] = mapped_column(String(40), nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    reward_exp: Mapped[int] = mapped_column(Integer, nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
