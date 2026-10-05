"""python -m app.seed [--reset] [--if-empty]"""

import argparse

from app.db.session import SessionLocal
from app.models import User
from app.seed.demo import run
from app.seed.reference import seed_reference


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed reference data and demo data")
    ap.add_argument("--reset", action="store_true", help="wipe all data before seeding")
    ap.add_argument("--if-empty", action="store_true", help="seed demo data only if there are no users")
    ap.add_argument("--reference-only", action="store_true", help="only reference data and the item bank")
    args = ap.parse_args()
    with SessionLocal() as db:
        if args.reference_only:
            seed_reference(db)
            print("reference data seeded")
            return
        if args.if_empty and db.query(User).count() > 0:
            seed_reference(db)  # keep the item bank up to date
            print("database is not empty — demo seed skipped")
            return
        stats = run(db, wipe=args.reset)
        print("demo data seeded:", stats)


if __name__ == "__main__":
    main()
