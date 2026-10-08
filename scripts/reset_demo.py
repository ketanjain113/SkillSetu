from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.database import SessionLocal
from app.demo_reset import reset_demo_state


def main() -> None:
    db = SessionLocal()
    try:
        counts = reset_demo_state(db)
    finally:
        db.close()
    print(
        "Reset configured demo database and restored trade packs: "
        f"{counts['users']} users, {counts['candidates']} candidates, "
        f"{counts['assessments']} assessments, {counts['demo_scores']} demo scores."
    )


if __name__ == '__main__':
    main()
