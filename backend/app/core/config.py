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

    # Public URLs used to build OAuth/Duo redirects back into the SPA
    FRONTEND_URL: str = "http://localhost:5173"
    API_PUBLIC_URL: str = "http://localhost:8000"

    # Microsoft Entra ID (UTEP campus SSO). Duo MFA is enforced by UTEP on the IdP.
    ENTRA_TENANT_ID: str = ""
    ENTRA_CLIENT_ID: str = ""
    ENTRA_CLIENT_SECRET: str = ""
    ENTRA_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/sso/callback"
    ENTRA_DOMAIN_HINT: str = "utep.edu"
    ENTRA_LOGIN_HINT_SUFFIX: str = ""

    # When true and Entra is configured, hide local password login in /auth/providers.
    AUTH_REQUIRE_UTEP_SSO: bool = False
    # Keep educational password + code MFA available for demos unless SSO is required.
    AUTH_ALLOW_LOCAL_LOGIN: bool = True

    # Duo Universal Prompt — optional MFA for the local password path only.
    DUO_CLIENT_ID: str = ""
    DUO_CLIENT_SECRET: str = ""
    DUO_API_HOSTNAME: str = ""
    DUO_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/duo/callback"

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Same database, sync psycopg2 driver -- used by Alembic and one-off scripts."""
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg2")


settings = Settings()
