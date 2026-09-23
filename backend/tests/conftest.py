"""Reset the async SQLAlchemy engine between tests (asyncpg ≠ closed event loops)."""
import pytest

from app.db.session import engine

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(autouse=True)
async def _reset_async_engine():
    await engine.dispose()
    yield
    await engine.dispose()
