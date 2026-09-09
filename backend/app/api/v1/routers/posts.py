"""추천 게시판 (F-BOARD). Phase 3 — basic CRUD implemented, moderation lives in admin."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import CurrentUser, DbSession
from app.models.enums import ContentStatus
from app.models.post import Comment, Post, PostLike
from app.models.user import UserStat
from app.schemas.post import (
    CommentCreate,
    CommentOut,
    PostCreate,
    PostOut,
)

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("", response_model=list[PostOut])
async def list_posts(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Post]:
    return list(
        (
            await db.execute(
                select(Post)
                .where(Post.status == ContentStatus.PUBLISHED)
                .order_by(Post.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )


@router.post("", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: PostCreate, db: DbSession, user: CurrentUser
) -> Post:
    stat = await db.get(UserStat, user.id)
    post = Post(
        user_id=user.id,
        store_id=payload.store_id,
        title=payload.title,
        content=payload.content,
        author_tier_snapshot=stat.tier_level if stat else 1,
        author_flag_count_snapshot=(
            (stat.gold_flag_count + stat.silver_flag_count) if stat else 0
        ),
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


@router.get("/{post_id}", response_model=PostOut)
async def get_post(post_id: int, db: DbSession) -> Post:
    post = await db.get(Post, post_id)
    if post is None or post.status != ContentStatus.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return post


@router.get("/{post_id}/comments", response_model=list[CommentOut])
async def list_comments(post_id: int, db: DbSession) -> list[Comment]:
    return list(
        (
            await db.execute(
                select(Comment)
                .where(
                    Comment.post_id == post_id,
                    Comment.status == ContentStatus.PUBLISHED,
                )
                .order_by(Comment.created_at.asc())
            )
        )
        .scalars()
        .all()
    )


@router.post("/{post_id}/like", status_code=status.HTTP_204_NO_CONTENT)
async def like_post(post_id: int, db: DbSession, user: CurrentUser) -> None:
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    db.add(PostLike(post_id=post_id, user_id=user.id))
    post.like_count += 1
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="이미 좋아요한 글입니다."
        ) from exc


@router.post(
    "/{post_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    post_id: int, payload: CommentCreate, db: DbSession, user: CurrentUser
) -> Comment:
    if await db.get(Post, post_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    comment = Comment(post_id=post_id, user_id=user.id, content=payload.content)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment
