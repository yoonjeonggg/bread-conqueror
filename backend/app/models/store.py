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

from app.db.base_class import Base, BigIntPK, TimestampMixin
from app.models.enums import StoreCreatedSource, StoreStatus

if TYPE_CHECKING:
    from app.models.flag import Flag


class Store(Base, TimestampMixin):
    __tablename__ = "stores"
    __table_args__ = (Index("idx_stores_location", "lat", "lng"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    region_sido: Mapped[str | None] = mapped_column(String(50), nullable=True)
    lat: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    lng: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_source: Mapped[StoreCreatedSource] = mapped_column(
        Enum(StoreCreatedSource), nullable=False
    )
    is_verified_owner: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    status: Mapped[StoreStatus] = mapped_column(
        Enum(StoreStatus), nullable=False, default=StoreStatus.ACTIVE
    )

    stat: Mapped[StoreStat] = relationship(
        back_populates="store", uselist=False, cascade="all, delete-orphan"
    )
    flags: Mapped[list[Flag]] = relationship(back_populates="store")


class StoreStat(Base):
    __tablename__ = "store_stats"

    store_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stores.id", ondelete="CASCADE"), primary_key=True
    )
    gold_flag_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    silver_flag_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conqueror_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_rating: Mapped[Decimal | None] = mapped_column(
        Numeric(2, 1), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    store: Mapped[Store] = relationship(back_populates="stat")
