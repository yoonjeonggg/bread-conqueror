from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, BigIntPK


class StoreQrToken(Base):
    """정복용 QR 토큰 (로드맵 5단계).

    인증된 매장 소유자가 발급한다. 손님이 매장 QR을 스캔하면 토큰이 매장을
    가리키므로 GPS 반경 검사 없이 골드 깃발을 발급한다.
    """

    __tablename__ = "store_qr_tokens"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stores.id"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def is_active(self, now: datetime) -> bool:
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at <= now:
            return False
        return not (
            self.max_uses is not None and self.use_count >= self.max_uses
        )
