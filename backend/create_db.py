"""One-shot: create all tables in `bid_wise` from SQLAlchemy models.

Run from backend/ as a script:
    cd backend && python create_db.py

Idempotent — `create_all` skips existing tables. For schema changes after
the first run, switch to alembic (already scaffolded under ../alembic/).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# allow running from project root or from backend/
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from app.core.database import Base, engine  # noqa: E402
from app import models  # noqa: F401, E402  (registers all models on Base)


def main() -> int:
    print(f"[+] connecting to DB and creating tables")
    Base.metadata.create_all(bind=engine)
    # list created tables
    from sqlalchemy import inspect
    insp = inspect(engine)
    tables = sorted(insp.get_table_names())
    print(f"[+] tables present: {len(tables)}")
    for t in tables:
        cols = [c["name"] for c in insp.get_columns(t)]
        print(f"   {t}  ({len(cols)} cols)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
