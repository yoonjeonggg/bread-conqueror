from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# Verified against when the account doesn't exist, so a failed login costs the
# same bcrypt round either way and response time can't be used to probe which
# emails are registered.
_DUMMY_HASH = pwd_context.hash("bread-conqueror-timing-equalizer")


def burn_password_check(plain: str) -> None:
    pwd_context.verify(plain, _DUMMY_HASH)


def _create_token(subject: str | int, token_type: TokenType, expires: timedelta) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str | int) -> str:
    return _create_token(
        subject, "access", timedelta(minutes=settings.access_token_expire_minutes)
    )


def create_refresh_token(subject: str | int) -> str:
    return _create_token(
        subject, "refresh", timedelta(days=settings.refresh_token_expire_days)
    )


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    """Validate signature, expiry and token type; raises ``jwt.PyJWTError``."""
    claims = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["sub", "type", "iat", "exp"]},
    )
    if claims["type"] != expected_type:
        raise jwt.InvalidTokenError(f"expected a {expected_type} token")
    return claims


def token_subject(token: str, expected_type: TokenType) -> int:
    """User id carried by a valid token; raises ``jwt.PyJWTError`` otherwise."""
    try:
        return int(decode_token(token, expected_type)["sub"])
    except ValueError as exc:
        raise jwt.InvalidTokenError("malformed subject") from exc
