from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, BigIntPK, TimestampMixin
from app.models.enums import UserRole, UserStatus

if TYPE_CHECKING:
    from app.models.flag import Flag


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    nickname: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), nullable=False, default=UserRole.USER
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus), nullable=False, default=UserStatus.ACTIVE
    )

    stat: Mapped[UserStat] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    flags: Mapped[list[Flag]] = relationship(back_populates="user")


class UserStat(Base):
    __tablename__ = "user_stats"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    exp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tier_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    gold_flag_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    silver_flag_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conquered_store_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    received_like_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="stat")
