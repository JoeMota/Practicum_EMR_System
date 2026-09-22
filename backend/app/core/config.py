from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "UTEP Educational EHR API"
    API_V1_PREFIX: str = "/api/v1"

    # App runs async through asyncpg (must match docker-compose credentials)
    DATABASE_URL: str = "postgresql+asyncpg://emr:emr@localhost:5432/emr"

    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # short-lived tokens support FR-09 session timeout

    CORS_ORIGINS: list[str] = ["http://localhost:5173"]  # Vite dev server

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Same database, sync psycopg2 driver -- used by Alembic and one-off scripts."""
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg2")


settings = Settings()
