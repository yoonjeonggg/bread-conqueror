from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, BigIntPK
from app.models.enums import EvidenceType, FlagStatus, FlagType

if TYPE_CHECKING:
    from app.models.store import Store
    from app.models.user import User


class Flag(Base):
    __tablename__ = "flags"
    __table_args__ = (
        Index("idx_flags_user_store", "user_id", "store_id"),
        Index("idx_flags_store_type", "store_id", "type"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    store_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stores.id"), nullable=False
    )
    type: Mapped[FlagType] = mapped_column(Enum(FlagType), nullable=False)
    evidence_type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType), nullable=False
    )
    evidence_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    visited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lat_at_conquest: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    lng_at_conquest: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    exp_granted: Mapped[int] = mapped_column(Integer, nullable=False)
    is_flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[FlagStatus] = mapped_column(
        Enum(FlagStatus), nullable=False, default=FlagStatus.VALID
    )
    upgraded_from_silver: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="flags")
    store: Mapped[Store] = relationship(back_populates="flags")
