from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, BigIntPK


class TierPolicy(Base):
    __tablename__ = "tier_policies"

    tier_level: Mapped[int] = mapped_column(Integer, primary_key=True)
    tier_name: Mapped[str] = mapped_column(String(50), nullable=False)
    required_exp: Mapped[int] = mapped_column(Integer, nullable=False)
    gold_ratio_requirement: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2), nullable=True
    )


class PolicyConfig(Base):
    __tablename__ = "policy_configs"

    config_key: Mapped[str] = mapped_column(String(50), primary_key=True)
    config_value: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AdminActionLog(Base):
    __tablename__ = "admin_action_logs"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class VerificationCode(Base):
    """Email verification codes (F-AUTH). Referenced by the tech-stack spec."""

    __tablename__ = "verification_codes"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
