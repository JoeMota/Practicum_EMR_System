"""Fill Sprint 3 sample cases on a database that already has the demo accounts."""
import asyncio

from app.db.session import engine
from app.scripts.seed import ensure_live_demo


def main() -> None:
    async def _run() -> None:
        await ensure_live_demo()
        await engine.dispose()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
