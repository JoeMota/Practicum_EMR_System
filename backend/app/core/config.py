from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_UNSAFE_SECRETS = {"", "change-me", "change-me-to-a-long-random-string"}


def _as_asyncpg(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql+psycopg2://"):
        return "postgresql+asyncpg://" + url[len("postgresql+psycopg2://") :]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


def _strip_ssl_query(url: str) -> tuple[str, bool]:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    cleaned = urlunparse(parsed._replace(query=urlencode(query)))
    return cleaned, sslmode in {"require", "verify-ca", "verify-full"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "UTEP Educational EHR API"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "postgresql+asyncpg://emr:emr@localhost:5432/emr"
    database_ssl: bool = False

    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    NOTE_CONTENT_KEY: str = ""

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    CORS_ORIGIN_REGEX: str | None = None
    LEXICOMP_URL: str | None = None
    LEXICOMP_API_URL: str | None = None
    LEXICOMP_API_KEY: str | None = None
    AI_API_URL: str | None = None
    AI_API_KEY: str | None = None
    AI_MODEL: str = "assist"

    @model_validator(mode="after")
    def normalize(self) -> "Settings":
        url, ssl = _strip_ssl_query(_as_asyncpg(self.DATABASE_URL.strip()))
        self.DATABASE_URL = url
        self.database_ssl = ssl or self.database_ssl
        if self.ENVIRONMENT == "production" and self.JWT_SECRET_KEY.strip() in _UNSAFE_SECRETS:
            raise ValueError("JWT_SECRET_KEY must be a real secret when ENVIRONMENT=production")
        if self.ENVIRONMENT == "production" and not self.NOTE_CONTENT_KEY.strip():
            raise ValueError("NOTE_CONTENT_KEY must be set when ENVIRONMENT=production")
        return self

    @property
    def SYNC_DATABASE_URL(self) -> str:
        url = self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        if self.database_ssl and "sslmode=" not in url:
            joiner = "&" if "?" in url else "?"
            url = f"{url}{joiner}sslmode=require"
        return url


settings = Settings()
