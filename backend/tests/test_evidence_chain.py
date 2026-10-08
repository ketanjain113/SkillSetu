import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.evidence_chain import evidence_chain_hash, verify_evidence_chain
from app.main import _verify_saved_evidence_chain, public_verify, simulate_evidence_tampering, app
from app.models import Assessment, Candidate, CredentialRecord, EvidenceItem, User
from app.integrations import issue_verifiable_credential
from app.security import get_current_user


def test_evidence_chain_detects_tampered_records_and_links():
    first = {"video_sha256": "a" * 64, "timestamp": "2026-10-08T12:00:00Z", "geo": {"latitude": 1.25}}
    second = {"video_sha256": "b" * 64, "timestamp": "2026-10-08T12:01:00Z", "geo": {"latitude": 2.5}}
    first_hash = evidence_chain_hash("", first)
    second_hash = evidence_chain_hash(first_hash, second)
    entries = [
        {"id": 1, "proof_data": first, "previous_hash": "", "hash_chain": first_hash},
        {"id": 2, "proof_data": second, "previous_hash": first_hash, "hash_chain": second_hash},
    ]

    assert [result["valid"] for result in verify_evidence_chain(entries)] == [True, True]
    entries[0]["proof_data"] = {**first, "geo": {"latitude": 9.0}}
    assert [result["valid"] for result in verify_evidence_chain(entries)] == [False, False]


def test_verify_chain_endpoint_checks_saved_evidence_records():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    test_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = test_session()
    user = User(username="chain-worker", full_name="Chain Worker", role="worker", password_hash="not-used")
    db.add(user)
    db.flush()
    candidate = Candidate(user_id=user.id, trade="Domestic Electrician", region="Test")
    db.add(candidate)
    db.flush()
    assessment = Assessment(candidate_id=candidate.id, status="declared")
    db.add(assessment)
    db.commit()
    db.refresh(user)
    db.close()

    def override_db():
        session = test_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            saved = client.post(
                "/api/evidence",
                json={
                    "title": "camera evidence",
                    "sha256": "c" * 64,
                    "hash_chain": "client-supplied-value-must-be-ignored",
                    "geo": {"latitude": 1.25, "longitude": 2.5, "captured_at": "2026-10-08T12:00:00Z"},
                    "timestamp": "2026-10-08T12:00:00Z",
                    "liveness": {"challenge": "blink", "result": "passed", "confidence": 0.9},
                    "required_steps": ["test wiring"],
                    "steps": [{"step_id": "step-1", "name": "test wiring", "status": "done", "start_time": 1.2, "end_time": 3.4}],
                },
                headers={"Authorization": "Bearer test-token"},
            )
            assert saved.status_code == 200, saved.text
            assert saved.json()["hash_chain"] != "client-supplied-value-must-be-ignored"
            assert saved.json()["evidence_sufficiency"]["sufficient"] is True
            evidence_id = saved.json()["id"]
            chain = client.post("/api/evidence/verify-chain", headers={"Authorization": "Bearer test-token"})
            assert chain.status_code == 200
            assert chain.json()["valid"] is True
            assert chain.json()["verified_count"] == chain.json()["total_count"] == 1

            tamper_db = test_session()
            item = tamper_db.query(EvidenceItem).filter(EvidenceItem.id == evidence_id).one()
            proof = json.loads(item.proof_data)
            proof["geo"]["latitude"] = 99
            item.proof_data = json.dumps(proof)
            tamper_db.commit()
            tamper_db.close()

            tampered = client.post("/api/evidence/verify-chain", headers={"Authorization": "Bearer test-token"})
            assert tampered.status_code == 200
            assert tampered.json()["valid"] is False
            assert tampered.json()["results"][0]["valid"] is False
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_admin_tamper_demo_edits_stored_record_and_reports_broken_link():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    sessions = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    db = sessions()
    admin = User(username="tamper-admin", full_name="Tamper Admin", role="admin", password_hash="unused")
    worker = User(username="worker1", full_name="Worker One", role="worker", password_hash="unused")
    db.add_all([admin, worker])
    db.flush()
    db.add(Candidate(user_id=worker.id, trade="Demo trade", region="Demo"))
    db.commit()

    result = simulate_evidence_tampering(db, admin)
    chain = _verify_saved_evidence_chain(db)
    assert result["simulated"] is True
    assert chain["valid"] is False
    assert any(link["id"] == result["evidence_id"] for link in chain["broken_links"])
    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_public_certificate_checks_signature_hash_and_evidence_chain():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    sessions = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    db = sessions()
    worker = User(username="verified-worker", full_name="Verified Worker", role="worker", password_hash="unused")
    db.add(worker)
    db.flush()
    candidate = Candidate(user_id=worker.id, trade="Demo electrician", region="Demo")
    db.add(candidate)
    db.flush()
    assessment = Assessment(candidate_id=candidate.id, status="credential_issued")
    db.add(assessment)
    db.flush()
    credential = issue_verifiable_credential({
        "credential_id": f"urn:uuid:verification-test-{assessment.id}",
        "candidate_id": "did:example:worker-test",
        "trade": candidate.trade,
        "nsqf_level": 4,
    })
    db.add(CredentialRecord(
        assessment_id=assessment.id,
        credential_id=credential["id"],
        credential_json=json.dumps(credential, sort_keys=True),
    ))
    proof = {"video_sha256": "d" * 64, "geo": {}, "timestamp": "2026-10-08T12:00:00Z"}
    evidence_hash = evidence_chain_hash("", proof)
    db.add(EvidenceItem(
        assessment_id=assessment.id,
        title="Demo evidence",
        sha256=proof["video_sha256"],
        geo="{}",
        timestamp=proof["timestamp"],
        previous_hash="",
        hash_chain=evidence_hash,
        proof_data=json.dumps(proof, sort_keys=True, separators=(",", ":")),
    ))
    db.commit()

    valid = public_verify(assessment.id, db)
    assert valid["verified"] is True
    assert valid["signature_verified"] is True
    assert valid["evidence_chain_verified"] is True

    credential["credentialSubject"]["trade"] = "Tampered trade"
    stored = db.query(CredentialRecord).filter_by(assessment_id=assessment.id).one()
    stored.credential_json = json.dumps(credential)
    db.commit()
    invalid = public_verify(assessment.id, db)
    assert invalid["verified"] is False
    assert invalid["signature_verified"] is False
    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
