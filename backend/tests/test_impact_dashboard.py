from datetime import datetime, timedelta
from types import SimpleNamespace

from app.impact import build_impact_summary


def test_impact_summary_reports_proxy_funnel_timing_trade_and_demo_fairness():
    now = datetime(2026, 1, 1)
    candidate_a = SimpleNamespace(
        id=1, trade="Electrician", gender="woman", region="North", language="Hindi",
        demographics_are_demo=True,
    )
    candidate_b = SimpleNamespace(
        id=2, trade="Plumber", gender=None, region="South", language="English",
        demographics_are_demo=False,
    )
    assessments = [
        SimpleNamespace(id=10, candidate_id=1, status="credential_issued", created_at=now),
        SimpleNamespace(id=20, candidate_id=2, status="declared", created_at=now),
    ]
    records = [
        SimpleNamespace(assessment_id=10, competency_id="safety", review_round=1, score=4, ai_assisted=True, is_demo=True, created_at=now + timedelta(hours=2)),
        SimpleNamespace(assessment_id=10, competency_id="wiring", review_round=1, score=5, ai_assisted=True, is_demo=True, created_at=now + timedelta(hours=3)),
        SimpleNamespace(assessment_id=20, competency_id="safety", review_round=1, score=4, ai_assisted=False, is_demo=False, created_at=now + timedelta(hours=1)),
    ]

    summary = build_impact_summary(assessments, [candidate_a, candidate_b], records)

    assert summary["funnel"][0]["count"] == 2
    assert summary["funnel"][-1]["count"] == 1
    assert summary["time_per_candidate"]["assisted"] == {"seconds": 10800, "candidate_count": 1}
    assert summary["time_per_candidate"]["unassisted"] == {"seconds": 3600, "candidate_count": 1}
    assert summary["pass_rate_by_trade"][0]["eligible"] == 1
    assert summary["pass_rate_by_trade"][0]["pass_rate"] == 1.0
    woman_row = next(row for row in summary["fairness"]["gender"] if row["label"] == "woman")
    assert woman_row["includes_demo_data"] is True
    assert summary["includes_demo_data"] is True
    assert "Not an official" in summary["outcome_method"]
