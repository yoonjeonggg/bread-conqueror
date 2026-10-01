import jwt
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import or_, select

from app.core.dependencies import CurrentUser, DbSession
from app.core.redis import redis_client
from app.core.security import (
    burn_password_check,
    create_access_token,
    create_refresh_token,
    hash_password,
    token_subject,
    verify_password,
)
from app.models.enums import UserStatus
from app.models.user import User, UserStat
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserOut
from app.services import login_throttle

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(user_id: int) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


def _ensure_active(user: User) -> None:
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="이용이 제한된 계정입니다."
        )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DbSession) -> User:
    exists = (
        await db.execute(
            select(User).where(
                or_(User.email == payload.email, User.nickname == payload.nickname)
            )
        )
    ).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 이메일 또는 닉네임입니다.",
        )

    user = User(
        nickname=payload.nickname,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    user.stat = UserStat()
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: DbSession) -> TokenResponse:
    ip = request.client.host if request.client else "unknown"
    wait = await login_throttle.retry_after(redis_client, ip, payload.email)
    if wait is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요.",
            headers={"Retry-After": str(wait)},
        )

    user = (
        await db.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()
    if user is None or user.password_hash is None:
        burn_password_check(payload.password)
        authenticated = False
    else:
        authenticated = verify_password(payload.password, user.password_hash)
    if not authenticated:
        await login_throttle.record_failure(redis_client, ip, payload.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    await login_throttle.reset(redis_client, ip, payload.email)
    _ensure_active(user)
    return _issue_tokens(user.id)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: DbSession) -> TokenResponse:
    try:
        user_id = token_subject(payload.refresh_token, "refresh")
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 refresh token 입니다.",
        ) from exc

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    # a suspended/withdrawn account must not keep minting fresh tokens
    _ensure_active(user)
    return _issue_tokens(user.id)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user
