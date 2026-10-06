from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import io
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from fastapi import Header, HTTPException

from .config import settings

VC_REGISTRY: dict[str, dict[str, Any]] = {}
REVOCATION_LIST: list[dict[str, Any]] = [
    {
        "credential_id": "urn:uuid:demo-revoked-001",
        "reason": "Duplicate issuance detected in demo review",
        "revoked_at": "2026-10-06T00:00:00Z",
    }
]


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode("utf-8")


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _key_material_path() -> Path:
    return Path(__file__).resolve().parent / ".integration_keys.json"


def _ensure_key_material() -> dict[str, str]:
    path = _key_material_path()
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    payload = {
        "private_key_b64": base64.b64encode(
            private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption(),
            )
        ).decode("ascii"),
        "public_key_b64": base64.b64encode(
            public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode("ascii"),
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def _load_private_key() -> Ed25519PrivateKey:
    material = _ensure_key_material()
    private_key_bytes = base64.b64decode(material["private_key_b64"])
    return Ed25519PrivateKey.from_private_bytes(private_key_bytes)


def _load_public_key() -> Ed25519PublicKey:
    material = _ensure_key_material()
    public_key_bytes = base64.b64decode(material["public_key_b64"])
    return Ed25519PublicKey.from_public_bytes(public_key_bytes)


def _hash_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def issue_verifiable_credential(payload: dict[str, Any]) -> dict[str, Any]:
    credential_id = payload.get("credential_id") or f"urn:uuid:{uuid.uuid4()}"
    candidate_id = payload.get("candidate_id") or f"did:example:worker-{uuid.uuid4().hex[:8]}"
    trade = payload.get("trade") or "Domestic Electrician"
    nsqf_level = payload.get("nsqf_level") or 4
    hash_chain = _hash_value({
        "candidate_id": candidate_id,
        "trade": trade,
        "nsqf_level": nsqf_level,
    })

    credential_subject = {
        "id": candidate_id,
        "trade": trade,
        "nsqf_level": nsqf_level,
        "hash_chain": hash_chain,
        "status": "verified",
    }
    credential = {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://schema.org",
        ],
        "id": credential_id,
        "type": ["VerifiableCredential", "SkillSetuCredential"],
        "issuer": "did:example:skillsetu-issuer",
        "issuanceDate": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "credentialSubject": credential_subject,
    }
    signed_payload = {key: value for key, value in credential.items() if key != "proof"}
    private_key = _load_private_key()
    signature = private_key.sign(canonical_json(signed_payload))
    credential["proof"] = {
        "type": "Ed25519Signature2020",
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "verificationMethod": "did:example:skillsetu-issuer#key-1",
        "proofValue": base64.b64encode(signature).decode("ascii"),
    }
    VC_REGISTRY[credential_id] = credential
    return credential


def verify_verifiable_credential(credential_id: str) -> dict[str, Any]:
    credential = VC_REGISTRY.get(credential_id)
    if credential is None:
        return {"valid": False, "status": "not_found", "credential_id": credential_id, "hash_verified": False}

    proof = credential.get("proof")
    if not proof or "proofValue" not in proof:
        return {"valid": False, "status": "invalid_signature", "credential_id": credential_id, "hash_verified": False}

    signed_payload = {key: value for key, value in credential.items() if key != "proof"}
    expected_hash = _hash_value({
        "candidate_id": credential["credentialSubject"]["id"],
        "trade": credential["credentialSubject"]["trade"],
        "nsqf_level": credential["credentialSubject"]["nsqf_level"],
    })
    hash_verified = credential["credentialSubject"].get("hash_chain") == expected_hash

    try:
        public_key = _load_public_key()
        public_key.verify(
            base64.b64decode(proof["proofValue"]),
            canonical_json(signed_payload),
        )
        signature_valid = True
    except (ValueError, InvalidSignature):
        signature_valid = False

    valid = signature_valid and hash_verified
    return {
        "valid": valid,
        "status": "verified" if valid else "failed",
        "credential_id": credential_id,
        "hash_verified": hash_verified,
        "signature_verified": signature_valid,
        "issued_by": credential.get("issuer"),
    }


def get_revocations() -> dict[str, Any]:
    return {"revocations": REVOCATION_LIST}


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    if not x_api_key or x_api_key != settings.integration_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key


def push_ncvet_result(payload: dict[str, Any]) -> dict[str, Any]:
    event = {
        "event": "result.pushed",
        "candidate_id": payload.get("candidate_id"),
        "trade": payload.get("trade"),
        "score": payload.get("score"),
        "credential_id": payload.get("credential_id"),
        "pushed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    body = canonical_json(event)
    signature = hmac.new(settings.integration_api_key.encode("utf-8"), body, hashlib.sha256).hexdigest()
    attempt_count = 3
    return {
        "status": "queued",
        "webhook_url": "https://mock.ncvet.gov.in/webhooks/skillsetu",
        "signing_key": "skillsetu-demo-hmac-sha256",
        "signature": signature,
        "retry_count": attempt_count,
        "attempts": [
            {"attempt": index + 1, "status": "queued" if index < 2 else "failed"}
            for index in range(attempt_count)
        ],
        "payload": event,
    }


def build_result_csv() -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["candidate_id", "trade", "score", "status", "credential_id"])
    writer.writerow(["worker1", "Domestic Electrician", "4.5", "credential_issued", "urn:uuid:demo-vc-001"])
    writer.writerow(["worker2", "Plumber (General)", "4.0", "under_review", "urn:uuid:demo-vc-002"])
    writer.writerow(["worker3", "Tailor / Sewing Machine Operator", "3.8", "signed_off", "urn:uuid:demo-vc-003"])
    return output.getvalue()


def _build_pdf_bytes(title: str, lines: list[str]) -> bytes:
    content_lines = [
        "BT",
        "/F1 18 Tf",
        "72 770 Td",
        f"({ _escape_pdf_text(title) }) Tj",
        "ET",
    ]
    y = 730
    for line in lines:
        content_lines.extend([
            "BT",
            "/F1 12 Tf",
            f"72 {y} Td",
            f"({ _escape_pdf_text(line) }) Tj",
            "ET",
        ])
        y -= 20

    content = "\n".join(content_lines).encode("latin-1", errors="replace")
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n{content.decode('latin-1', errors='replace')}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    pdf = bytearray()
    pdf.extend(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n{obj}\nendobj\n".encode("latin-1", errors="replace"))

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin-1"))
    return bytes(pdf)


def build_certificate_pdf(assessment_id: int) -> bytes:
    return _build_pdf_bytes(
        "SkillSetu AI Certificate",
        [
            f"Credential ID: SKILLSETU-{assessment_id:05d}",
            "Trade: Domestic Electrician",
            "Status: Verified and hash-checked",
            "Assessor sign-off: accepted",
            "Demo export: realistic mock certificate",
        ],
    )


def build_competency_profile_pdf(assessment_id: int) -> bytes:
    return _build_pdf_bytes(
        "SkillSetu Competency Profile",
        [
            f"Assessment ID: {assessment_id}",
            "Safety: 4/5",
            "Wiring and fitting: 4/5",
            "Testing and fault finding: 5/5",
            "Recommended next step: supervised site work",
        ],
    )
