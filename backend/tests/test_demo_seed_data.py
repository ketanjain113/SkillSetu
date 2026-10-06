from app.database import SessionLocal
from app.main import ensure_seed_data
from app.models import Candidate, User


def test_seed_data_builds_realistic_demo_dataset():
    db = SessionLocal()
    try:
        db.query(Candidate).delete()
        db.query(User).delete()
        ensure_seed_data(db)
        db.commit()

        assert db.query(User).filter(User.role == "assessor").count() >= 8
        assert db.query(Candidate).count() >= 60

        trades = {candidate.trade for candidate in db.query(Candidate).all()}
        assert len(trades) >= 5
        assert "Domestic Electrician" in trades
        assert "Plumber (General)" in trades
    finally:
        db.close()
