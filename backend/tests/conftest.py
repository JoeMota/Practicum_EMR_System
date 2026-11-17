import asyncio
import os
from pathlib import Path
from urllib.parse import quote_plus

_TEST_DB_USER = os.getenv("EMR_TEST_DB_USER", "emr")
_TEST_DB_PASSWORD = os.getenv("EMR_TEST_DB_PASSWORD", "emr")
_TEST_DB_HOST = os.getenv("EMR_TEST_DB_HOST", "localhost")
_TEST_DB_PORT = int(os.getenv("EMR_TEST_DB_PORT", "5432"))
os.environ["DATABASE_URL"] = (
    f"postgresql+asyncpg://{quote_plus(_TEST_DB_USER)}:{quote_plus(_TEST_DB_PASSWORD)}"
    f"@{_TEST_DB_HOST}:{_TEST_DB_PORT}/emr_test"
)
os.environ["SEED_DEMO_PASSWORD"] = "practicum-demo"


def _prepare() -> None:
    import psycopg2
    from alembic import command
    from alembic.config import Config

    conn = psycopg2.connect(
        dbname="emr",
        user=_TEST_DB_USER,
        password=_TEST_DB_PASSWORD,
        host=_TEST_DB_HOST,
        port=_TEST_DB_PORT,
    )
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'emr_test'")
    if cursor.fetchone() is None:
        cursor.execute("CREATE DATABASE emr_test")
    cursor.close()
    conn.close()

    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")

    from app.db.session import engine
    from app.scripts.seed import seed

    async def _seed() -> None:
        await seed(None, None)
        await engine.dispose()

    asyncio.run(_seed())


_prepare()

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402


@pytest.fixture
async def db_session():
    from app.db.session import engine

    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest.fixture
async def client(db_session):
    from app.api.routes.auth import clear_login_rate_limits
    from app.db.session import get_db
    from app.main import app

    clear_login_rate_limits()

    async def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http
    app.dependency_overrides.clear()
    clear_login_rate_limits()
