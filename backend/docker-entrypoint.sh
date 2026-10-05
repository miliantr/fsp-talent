#!/bin/sh
set -e

echo "Waiting for the database..."
python - <<'PY'
import time
from sqlalchemy import create_engine, text
from app.core.config import get_settings

url = get_settings().database_url
for attempt in range(60):
    try:
        with create_engine(url).connect() as c:
            c.execute(text("SELECT 1"))
        break
    except Exception as e:  # noqa: BLE001
        print(f"  db not ready ({e.__class__.__name__}), retry {attempt + 1}/60")
        time.sleep(1)
else:
    raise SystemExit("database is not reachable")
PY

echo "Applying migrations..."
alembic upgrade head

echo "Seeding (demo data only into an empty database)..."
python -m app.seed --if-empty

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${WEB_CONCURRENCY:-2}" --proxy-headers
