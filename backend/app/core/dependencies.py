from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models.enums import UserRole, UserStatus
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login", auto_error=False
)

DbSession = Annotated[AsyncSession, Depends(get_db)]

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    db: DbSession,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    if not token:
        raise _CREDENTIALS_EXC
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise _CREDENTIALS_EXC
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise _CREDENTIALS_EXC from exc

    user = await db.get(User, user_id)
    if user is None:
        raise _CREDENTIALS_EXC
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active"
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]


async def get_optional_user(
    db: DbSession,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User | None:
    if not token:
        return None
    try:
        return await get_current_user(db, token)
    except HTTPException:
        return None


OptionalUser = Annotated[User | None, Depends(get_optional_user)]
