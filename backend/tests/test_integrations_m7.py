from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

API_KEY = "skillsetu-demo-api-key"


def test_verifiable_credential_issue_and_verify():
    response = client.post(
        "/api/integrations/vc/issue",
        json={
            "credential_id": "urn:uuid:demo-vc-001",
            "candidate_id": "worker1",
            "trade": "Domestic Electrician",
            "nsqf_level": 4,
            "hash_chain": "abc123",
        },
        headers={"X-API-Key": API_KEY},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["credential"]["proof"]["type"] == "Ed25519Signature2020"
    assert body["credential"]["proof"]["verificationMethod"]
    assert body["credential"]["credentialSubject"]["hash_chain"]

    verify = client.get(f"/api/public/vc/verify/{body['credential']['id']}")
    assert verify.status_code == 200, verify.text
    verify_body = verify.json()
    assert verify_body["valid"] is True
    assert verify_body["hash_verified"] is True


def test_ncvet_push_has_signature_and_retry_log():
    response = client.post(
        "/api/integrations/ncvet/push",
        json={
            "candidate_id": "worker1",
            "trade": "Domestic Electrician",
            "score": 4.5,
            "credential_id": "urn:uuid:demo-vc-001",
        },
        headers={"X-API-Key": API_KEY},
    )
    assert response.status_code == 202, response.text
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["signature"]
    assert payload["retry_count"] >= 1

    revocations = client.get("/api/integrations/revocations", headers={"X-API-Key": API_KEY})
    assert revocations.status_code == 200, revocations.text
    data = revocations.json()
    assert isinstance(data["revocations"], list)


def test_exports_and_openapi_are_available():
    csv_response = client.get("/api/integrations/exports/csv", headers={"X-API-Key": API_KEY})
    assert csv_response.status_code == 200, csv_response.text
    csv_text = csv_response.text
    assert "candidate_id" in csv_text
    assert "trade" in csv_text

    docs = client.get("/openapi.json")
    assert docs.status_code == 200, docs.text
    assert docs.json()["info"]["title"] == "SkillSetu AI API"
