from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_returns_aggregate_workflow_metrics():
    with TestClient(app) as client:
        response = client.get("/api/dashboard")

    assert response.status_code == 200
    summary = response.json()
    assert summary["candidate_count"] >= 60
    assert summary["assessment_count"] >= 0
    assert summary["average_time_per_candidate_seconds"] is None or summary["average_time_per_candidate_seconds"] >= 0
    assert isinstance(summary["krippendorff_alpha"], float)
    assert summary["metrics_are_demo_data"] is True
    assert set(summary["assessment_stage_counts"]) == {
        "registered",
        "declared",
        "evidence_captured",
        "under_review",
        "second_review",
        "moderation",
        "signed_off",
        "credential_issued",
        "appeal",
    }
