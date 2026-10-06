from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'backend'
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.database import SessionLocal
from app.main import ensure_seed_data
from app.models import Candidate, User
from app.trade_packs import DEFAULT_TRADE_PACKS, save_trade_packs


def main() -> None:
    db_path = ROOT / 'skillsetu.db'
    if db_path.exists():
        db_path.unlink()
    save_trade_packs(DEFAULT_TRADE_PACKS)
    db = SessionLocal()
    try:
        ensure_seed_data(db)
        db.commit()
        user_count = db.query(User).count()
        candidate_count = db.query(Candidate).count()
    finally:
        db.close()
    print(f'Reset demo state: cleared database, restored packs, and seeded {user_count} users and {candidate_count} candidates.')


if __name__ == '__main__':
    main()
