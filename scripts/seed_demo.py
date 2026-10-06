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
    save_trade_packs(DEFAULT_TRADE_PACKS)
    db = SessionLocal()
    try:
        ensure_seed_data(db)
        db.commit()
        user_count = db.query(User).count()
        candidate_count = db.query(Candidate).count()
    finally:
        db.close()
    print(f'Seeded demo data: {user_count} users, {candidate_count} candidates, and multi-trade packs restored.')


if __name__ == '__main__':
    main()
