from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, BigIntPK
from app.models.enums import ClaimStatus


class StoreClaim(Base):
    __tablename__ = "store_claims"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stores.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    business_license_image_url: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus), nullable=False, default=ClaimStatus.PENDING
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
