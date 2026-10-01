"""Brute-force guard for POST /auth/login.

Failed attempts are counted in Redis per (client IP, email) inside a sliding
lockout window. Keying on the pair rather than the email alone means an
attacker can't lock a victim out of their own account from elsewhere.

Redis being down must not take login down with it, so every call fails open.
"""

from __future__ import annotations

import hashlib
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)


def _key(ip: str, email: str) -> str:
    # hash so raw emails never sit in Redis as key names
    digest = hashlib.sha256(f"{ip}|{email.lower()}".encode()).hexdigest()
    return f"login:fail:{digest}"


async def retry_after(redis: Redis, ip: str, email: str) -> int | None:
    """Seconds until the pair may try again, or None when not locked out."""
    key = _key(ip, email)
    try:
        failures = await redis.get(key)
        if failures is None or int(failures) < settings.login_max_attempts:
            return None
        ttl = await redis.ttl(key)
    except RedisError:
        logger.warning("login throttle unavailable; allowing attempt", exc_info=True)
        return None
    return max(ttl, 1)


async def record_failure(redis: Redis, ip: str, email: str) -> None:
    key = _key(ip, email)
    try:
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, settings.login_lockout_seconds)
        await pipe.execute()
    except RedisError:
        logger.warning("login throttle unavailable; failure not recorded", exc_info=True)


async def reset(redis: Redis, ip: str, email: str) -> None:
    try:
        await redis.delete(_key(ip, email))
    except RedisError:
        logger.warning("login throttle unavailable; counter not cleared", exc_info=True)
