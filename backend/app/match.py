from __future__ import annotations

import math
import re
from typing import Any, Dict, List

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    MODEL_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency fallback
    MODEL_AVAILABLE = False
    SentenceTransformer = None
    np = None


def normalize_text(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def lexical_similarity(query: str, candidate: str) -> float:
    q_tokens = set(normalize_text(query).split())
    c_tokens = set(normalize_text(candidate).split())
    if not q_tokens and not c_tokens:
        return 0.0
    overlap = q_tokens & c_tokens
    return len(overlap) / max(len(q_tokens | c_tokens), 1)


def rank_qualification_packs(text: str, packs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rank a task declaration against QP/NOS packs. Uses real sentence embeddings when available,
    with lexical fallback so demo remains functional offline without external downloads.
    """
    normalized = normalize_text(text)
    results: List[Dict[str, Any]] = []

    if MODEL_AVAILABLE and np is not None:
        model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM")
        texts = [text] + [p["summary"] + " " + " ".join(p["keywords"]) for p in packs]
        embeddings = model.encode(texts)
        query_embedding = embeddings[0]
        similarities = np.dot(embeddings[1:], query_embedding) / (
            np.linalg.norm(embeddings[1:], axis=1) * np.linalg.norm(query_embedding)
        )
        for idx, pack in enumerate(packs):
            lexical = lexical_similarity(text, pack["summary"] + " " + " ".join(pack["keywords"]))
            similarity = float(similarities[idx])
            confidence = max(0.25, min(0.99, round((similarity * 0.7 + lexical * 0.3), 4)))
            results.append({
                "pack_id": pack["pack_id"],
                "title": pack["title"],
                "confidence": confidence,
                "summary": pack["summary"],
                "skill_gaps": pack["skill_gaps"],
            })
    else:
        for pack in packs:
            lexical = lexical_similarity(text, pack["summary"] + " " + " ".join(pack["keywords"]))
            score = min(0.96, max(0.2, round(0.45 + lexical * 0.55, 4)))
            results.append({
                "pack_id": pack["pack_id"],
                "title": pack["title"],
                "confidence": score,
                "summary": pack["summary"],
                "skill_gaps": pack["skill_gaps"],
            })

    results.sort(key=lambda item: item["confidence"], reverse=True)
    return results[:3]


def hash_chain(values: List[str]) -> str:
    import hashlib

    chain = values[0] if values else ""
    for value in values[1:]:
        chain = hashlib.sha256((chain + value).encode()).hexdigest()
    return chain
