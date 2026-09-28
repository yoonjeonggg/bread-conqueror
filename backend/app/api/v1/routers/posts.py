"""추천 게시판 (F-BOARD). Phase 3 — basic CRUD implemented, moderation lives in admin."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, DbSession
from app.models.enums import ContentStatus, NotificationType
from app.models.post import Comment, Post, PostLike
from app.models.user import UserStat
from app.schemas.post import (
    CommentCreate,
    CommentOut,
    PostCreate,
    PostOut,
)
from app.services import notification_service

router = APIRouter(prefix="/posts", tags=["posts"])


LIKE_ESCAPE = "\\"


def _escape_like(term: str) -> str:
    # user input is a literal search term, not a LIKE pattern
    return term.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2).replace("%", r"\%").replace("_", r"\_")


async def _published_post(db: AsyncSession, post_id: int) -> Post:
    post = await db.get(Post, post_id)
    if post is None or post.status != ContentStatus.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return post


@router.get("", response_model=list[PostOut])
async def list_posts(
    db: DbSession,
    q: Annotated[str | None, Query(max_length=100)] = None,
    store_id: Annotated[int | None, Query(gt=0)] = None,
    sort: Literal["recent", "popular"] = "recent",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Post]:
    stmt = select(Post).where(Post.status == ContentStatus.PUBLISHED)
    if q and q.strip():
        like = f"%{_escape_like(q.strip())}%"
        stmt = stmt.where(
            or_(
                Post.title.ilike(like, escape=LIKE_ESCAPE),
                Post.content.ilike(like, escape=LIKE_ESCAPE),
            )
        )
    if store_id is not None:
        stmt = stmt.where(Post.store_id == store_id)
    order = Post.like_count.desc() if sort == "popular" else Post.created_at.desc()
    stmt = stmt.order_by(order, Post.id.desc()).limit(limit).offset(offset)
    return list((await db.execute(stmt)).scalars().all())


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
    return await _published_post(db, post_id)


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
    post = await _published_post(db, post_id)
    db.add(PostLike(post_id=post_id, user_id=user.id))
    try:
        # flush the like first so a duplicate fails here, before any side effects
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="이미 좋아요한 글입니다."
        ) from exc
    # increment in SQL: `post.like_count += 1` loses likes that land concurrently
    await db.execute(
        update(Post)
        .where(Post.id == post_id)
        .values(like_count=Post.like_count + 1)
        .execution_options(synchronize_session=False)
    )
    await notification_service.create(
        db,
        recipient_id=post.user_id,
        actor_id=user.id,
        type=NotificationType.POST_LIKE,
        message=f"{user.nickname}님이 '{post.title}' 글을 좋아합니다.",
        target_type="POST",
        target_id=post_id,
    )
    await db.commit()


@router.post(
    "/{post_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    post_id: int, payload: CommentCreate, db: DbSession, user: CurrentUser
) -> Comment:
    post = await _published_post(db, post_id)
    comment = Comment(post_id=post_id, user_id=user.id, content=payload.content)
    db.add(comment)
    await notification_service.create(
        db,
        recipient_id=post.user_id,
        actor_id=user.id,
        type=NotificationType.POST_COMMENT,
        message=f"{user.nickname}님이 '{post.title}' 글에 댓글을 남겼습니다.",
        target_type="POST",
        target_id=post_id,
    )
    await db.commit()
    await db.refresh(comment)
    return comment
