import logging
from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# HS256 keys shorter than the 256-bit digest are brute-forceable offline
MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "Bread Conqueror API"
    environment: Literal["local", "production"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Database / cache
    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14
    # brute-force guard on POST /auth/login, counted per (client IP, email)
    login_max_attempts: int = 5
    login_lockout_seconds: int = 300

    # Storage
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    s3_bucket_name: str | None = None
    aws_region: str = "ap-northeast-2"

    # External map APIs
    kakao_map_api_key: str | None = None
    naver_map_client_id: str | None = None
    naver_map_client_secret: str | None = None

    @model_validator(mode="after")
    def _check_secrets(self) -> "Settings":
        if len(self.jwt_secret_key) < MIN_JWT_SECRET_LENGTH:
            if self.environment == "production":
                raise ValueError(
                    f"JWT_SECRET_KEY must be at least {MIN_JWT_SECRET_LENGTH} characters "
                    "in production"
                )
            logger.warning("JWT_SECRET_KEY is weak; set a long random value before deploying")
        if self.environment == "production" and self.debug:
            raise ValueError("DEBUG must be off in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def sync_database_url(self) -> str:
        """Alembic / sync tooling needs a non-async driver URL."""
        return self.database_url.replace("+aiomysql", "+pymysql").replace(
            "+asyncmy", "+pymysql"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
