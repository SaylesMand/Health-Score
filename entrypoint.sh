#!/bin/sh
set -e

if [ "$RUN_MIGRATIONS" = "1" ]; then
    echo "[entrypoint] Running alembic migrations..."
    alembic upgrade head
    echo "[entrypoint] Running seed_db.py..."
    python scripts/seed_db.py
fi

exec "$@"
