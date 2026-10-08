from app.database import SessionLocal
from app.main import ensure_seed_data, load_calibration_data
from app.models import Assessment, Candidate, ScoreRecord, User
from app.seed_data import COMPETENCIES


def test_seed_data_builds_realistic_demo_dataset():
    db = SessionLocal()
    try:
        db.query(Candidate).delete()
        db.query(User).delete()
        ensure_seed_data(db)
        db.commit()

        assert db.query(User).filter(User.role == "assessor").count() >= 8
        assert db.query(User).filter(User.role == "moderator").count() >= 1
        assert db.query(Candidate).count() >= 60
        demo_assessments = db.query(Assessment).filter(
            Assessment.declared_text.like("DEMO_CALIBRATION_DATA%")
        ).count()
        demo_scores = db.query(ScoreRecord).filter(ScoreRecord.is_demo.is_(True)).count()
        assert demo_assessments == 60
        assert demo_scores == 60 * 8 * len(COMPETENCIES)
        assert db.query(ScoreRecord).filter(
            ScoreRecord.is_demo.is_(True),
            ScoreRecord.ai_assisted.is_(True),
        ).count() > 0

        trades = {candidate.trade for candidate in db.query(Candidate).all()}
        assert len(trades) >= 5
        assert "Domestic Electrician" in trades
        assert "Plumber (General)" in trades
        ensure_seed_data(db)
        assert db.query(Assessment).filter(
            Assessment.declared_text.like("DEMO_CALIBRATION_DATA%")
        ).count() == 60
        assert db.query(ScoreRecord).filter(ScoreRecord.is_demo.is_(True)).count() == demo_scores
        summary, _ = load_calibration_data(db)
        assert summary["demo_data"] is True
        assert summary["sample_count"] == demo_scores
        assert len(summary["assessor_severity"]) == 8
        assert len({row["severity"] for row in summary["assessor_severity"]}) >= 5
        assert summary["alpha_over_time"]
        assert summary["drift_alerts"]
        assert any(report["drift"] >= summary["drift_threshold"] for report in summary["report_cards"])
        assert summary["assistance_comparison"]["assisted"]["n"] > 0
        assert summary["assistance_comparison"]["unassisted"]["n"] > 0
    finally:
        db.close()
