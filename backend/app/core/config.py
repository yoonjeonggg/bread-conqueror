from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "Bread Conqueror API"
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

    # Storage
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    s3_bucket_name: str | None = None
    aws_region: str = "ap-northeast-2"

    # External map APIs
    kakao_map_api_key: str | None = None
    naver_map_client_id: str | None = None
    naver_map_client_secret: str | None = None

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
