import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Assessment, AuditLog, Candidate, ModerationRecord, ReviewAssignment, ScoreRecord, User
from app.security import get_current_user
from app.seed_data import COMPETENCIES
from app import review_workflow


@pytest.fixture
def review_setup():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    sessions = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    db = sessions()
    primary = User(username="primary", full_name="Primary", role="assessor", centre="North", password_hash="unused")
    second = User(username="second", full_name="Second", role="assessor", centre="South", password_hash="unused")
    moderator = User(username="moderator", full_name="Moderator", role="moderator", password_hash="unused")
    worker = User(username="worker", full_name="Worker", role="worker", password_hash="unused")
    db.add_all([primary, second, moderator, worker])
    db.flush()
    candidate = Candidate(user_id=worker.id, trade="Electrician", region="North")
    db.add(candidate)
    db.flush()
    assessment = Assessment(candidate_id=candidate.id, status="declared")
    db.add(assessment)
    db.commit()
    principal = {"user": primary}

    def override_db():
        session = sessions()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: principal["user"]
    try:
        with TestClient(app) as client:
            yield client, principal, {"primary": primary, "second": second, "moderator": moderator}, sessions, assessment.id
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def submit_score(client, assessment_id, competency_id, score, reason=None):
    return client.post("/api/score", json={
        "assessment_id": assessment_id,
        "competency_id": competency_id,
        "score": score,
        "explanation": "Assessment against the evidence and rubric.",
        "override_reason": reason,
    }, headers={"Authorization": "Bearer test"})


def test_sampling_uses_config_and_never_skips_flagged_or_low_confidence(monkeypatch):
    monkeypatch.setenv("SECOND_REVIEW_SAMPLE_RATE", "0.2")
    monkeypatch.setattr(review_workflow.random, "random", lambda: 0.99)
    assert not review_workflow.needs_second_review(flagged=False, confidence=0.8)
    assert review_workflow.needs_second_review(flagged=True, confidence=0.8)
    assert review_workflow.needs_second_review(flagged=False, confidence=0.64)
    monkeypatch.setenv("SECOND_REVIEW_SAMPLE_RATE", "1")
    assert review_workflow.needs_second_review(flagged=False, confidence=0.8)


def test_sampling_assigns_an_assessor_from_a_different_centre(review_setup, monkeypatch):
    client, principal, users, _, assessment_id = review_setup
    monkeypatch.setenv("SECOND_REVIEW_SAMPLE_RATE", "1")
    result = submit_score(client, assessment_id, COMPETENCIES[0]["id"], 4)
    assert result.status_code == 200, result.text
    assert result.json()["second_review_assigned"] is True
    assert result.json()["assessment_status"] == "second_review"

    db = review_setup[3]()
    assignment = db.query(ReviewAssignment).filter_by(assessment_id=assessment_id).one()
    assigned = db.query(User).filter_by(id=assignment.assessor_id).one()
    primary = db.query(User).filter_by(id=assignment.primary_assessor_id).one()
    assert assigned.id == users["second"].id
    assert assigned.id != primary.id
    assert assigned.centre != primary.centre
    db.close()

    principal["user"] = users["second"]
    queue = client.get("/api/reviews/queue", headers={"Authorization": "Bearer test"})
    assert queue.status_code == 200
    assert queue.json()["assignments"][0]["assessment_id"] == assessment_id


def test_assessor_blinding_is_enforced_by_api_until_their_own_score(review_setup, monkeypatch):
    client, principal, users, _, assessment_id = review_setup
    monkeypatch.setenv("SECOND_REVIEW_SAMPLE_RATE", "1")
    before = client.get(f"/api/assessments/{assessment_id}/review", headers={"Authorization": "Bearer test"})
    assert before.status_code == 200
    assert "ai_draft" not in before.text
    assert client.get(f"/api/calibration/explainability/{assessment_id}", headers={"Authorization": "Bearer test"}).status_code == 403

    payload = {
        "assessment_id": assessment_id,
        "competency_id": COMPETENCIES[0]["id"],
        "score": 3,
        "ai_draft": 1,
        "explanation": "Independent score",
    }
    rejected = client.post("/api/score", json=payload, headers={"Authorization": "Bearer test"})
    assert rejected.status_code == 422
    assert submit_score(client, assessment_id, COMPETENCIES[0]["id"], 3).status_code == 400
    assert submit_score(client, assessment_id, COMPETENCIES[0]["id"], 3, "Evidence supports the higher descriptor.").status_code == 200
    after = client.get(f"/api/assessments/{assessment_id}/review", headers={"Authorization": "Bearer test"})
    assert after.status_code == 200
    assert after.json()["scores"][0]["ai_draft"] == 4

    principal["user"] = users["second"]
    blind_second = client.get(f"/api/assessments/{assessment_id}/review", headers={"Authorization": "Bearer test"})
    assert blind_second.status_code == 200
    assert blind_second.json()["scores"] == []
    assert "ai_draft" not in blind_second.text
    principal["user"] = users["moderator"]
    moderator_audit = client.get("/api/audit", headers={"Authorization": "Bearer test"})
    assert all(entry["action"] != "score_submitted" for entry in moderator_audit.json()["logs"])


def test_score_rejects_invalid_transition_without_persisting_record(review_setup):
    client, _, _, sessions, assessment_id = review_setup
    db = sessions()
    db.query(Assessment).filter_by(id=assessment_id).one().status = "registered"
    db.commit()
    db.close()
    result = submit_score(client, assessment_id, COMPETENCIES[0]["id"], 4)
    assert result.status_code == 409
    db = sessions()
    assert db.query(ScoreRecord).filter_by(assessment_id=assessment_id).count() == 0
    db.close()


def test_status_api_cannot_skip_assignment_or_score_completion(review_setup):
    client, _, _, sessions, assessment_id = review_setup
    db = sessions()
    db.query(Assessment).filter_by(id=assessment_id).one().status = "under_review"
    db.commit()
    db.close()
    headers = {"Authorization": "Bearer test"}
    second_review = client.patch(f"/api/assessments/{assessment_id}/status", json={"status": "second_review"}, headers=headers)
    assert second_review.status_code == 409
    sign_off = client.patch(f"/api/assessments/{assessment_id}/status", json={"status": "signed_off"}, headers=headers)
    assert sign_off.status_code == 409
    assert client.get(f"/api/certificate/{assessment_id}", headers=headers).status_code == 409


def test_two_assessor_disagreement_moderates_and_records_decision(review_setup, monkeypatch):
    client, principal, users, sessions, assessment_id = review_setup
    monkeypatch.setenv("SECOND_REVIEW_SAMPLE_RATE", "1")
    competency_ids = [item["id"] for item in COMPETENCIES]
    for competency_id in competency_ids:
        result = submit_score(client, assessment_id, competency_id, 2, "Evidence does not satisfy the AI draft descriptor.")
        assert result.status_code == 200, result.text

    principal["user"] = users["second"]
    for competency_id in competency_ids:
        result = submit_score(client, assessment_id, competency_id, 4, "Observed evidence supports the higher descriptor.")
        assert result.status_code == 200, result.text
    status = client.get(f"/api/assessments/{assessment_id}/status", headers={"Authorization": "Bearer test"})
    assert status.json()["status"] == "moderation"

    principal["user"] = users["moderator"]
    packet = client.get(f"/api/assessments/{assessment_id}/review", headers={"Authorization": "Bearer test"})
    assert packet.status_code == 200
    assert len(packet.json()["scores"]) == len(competency_ids) * 2
    assert all(score["ai_draft"] == 4 for score in packet.json()["scores"])

    rationale = "The recorded work evidence was reviewed against the competency rubric."
    decision = client.post("/api/moderation", json={
        "assessment_id": assessment_id,
        "rationale": rationale,
        "final_scores": {competency_id: 3 for competency_id in competency_ids},
        "override_reasons": {competency_id: "Final rating reflects direct evidence and both assessor notes." for competency_id in competency_ids},
    }, headers={"Authorization": "Bearer test"})
    assert decision.status_code == 200, decision.text
    assert decision.json()["status"] == "signed_off"

    db = sessions()
    saved = db.query(ModerationRecord).filter_by(assessment_id=assessment_id).one()
    assert saved.rationale == rationale
    assert json.loads(saved.final_scores) == {competency_id: 3 for competency_id in competency_ids}
    assert len(json.loads(saved.overrides)) == len(competency_ids)
    assert db.query(ScoreRecord).filter_by(assessment_id=assessment_id).count() == len(competency_ids) * 2
    actions = {entry.action for entry in db.query(AuditLog).all()}
    assert {"score_submitted", "second_review_assigned", "moderation_escalated", "moderation_decision"} <= actions
    db.close()

    principal["user"] = users["primary"]
    certificate = client.get(f"/api/certificate/{assessment_id}", headers={"Authorization": "Bearer test"})
    assert certificate.status_code == 200
    final_status = client.get(f"/api/assessments/{assessment_id}/status", headers={"Authorization": "Bearer test"})
    assert final_status.json()["status"] == "credential_issued"
