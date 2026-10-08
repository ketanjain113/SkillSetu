import hashlib
import json
from typing import Any


def canonical_evidence_json(record: dict[str, Any]) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def evidence_chain_hash(previous_hash: str, record: dict[str, Any]) -> str:
    content = f"{previous_hash}{canonical_evidence_json(record)}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def verify_evidence_chain(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previous_hash = ""
    results = []
    for entry in entries:
        record = entry.get("proof_data")
        stored_previous = entry.get("previous_hash") or ""
        expected_hash = evidence_chain_hash(previous_hash, record) if isinstance(record, dict) else ""
        if not isinstance(record, dict):
            reason = "invalid_or_mismatched_proof_data"
        elif stored_previous != previous_hash:
            reason = "broken_previous_link"
        elif entry.get("hash_chain") != expected_hash:
            reason = "record_hash_mismatch"
        else:
            reason = None
        results.append({
            "id": entry.get("id"),
            "valid": reason is None,
            "hash": entry.get("hash_chain"),
            "reason": reason,
        })
        previous_hash = expected_hash
    return results
