#!/bin/sh
set -e
alembic upgrade head
python -m app.scripts.ensure_live_demo
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
