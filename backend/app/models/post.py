from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, BigIntPK
from app.models.enums import ContentStatus


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    store_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("stores.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_tier_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    author_flag_count_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    report_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus), nullable=False, default=ContentStatus.PUBLISHED
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    comments: Mapped[list[Comment]] = relationship(back_populates="post")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("posts.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus), nullable=False, default=ContentStatus.PUBLISHED
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    post: Mapped[Post] = relationship(back_populates="comments")


class PostLike(Base):
    __tablename__ = "post_likes"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_post_likes_post_user"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("posts.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
