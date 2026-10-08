from __future__ import annotations

from sqlalchemy.orm import Session

from .integrations import VC_REGISTRY
from .models import (
    Assessment,
    AuditLog,
    Candidate,
    CredentialRecord,
    EvidenceItem,
    ModerationRecord,
    ReviewAssignment,
    ScoreRecord,
    User,
)
from .trade_packs import DEFAULT_TRADE_PACKS, save_trade_packs


def reset_demo_state(db: Session) -> dict[str, int]:
    for model in (
        AuditLog,
        ModerationRecord,
        ReviewAssignment,
        ScoreRecord,
        EvidenceItem,
        CredentialRecord,
        Assessment,
        Candidate,
        User,
    ):
        db.query(model).delete(synchronize_session=False)
    db.commit()
    save_trade_packs(DEFAULT_TRADE_PACKS)
    VC_REGISTRY.clear()

    from .main import ensure_seed_data

    ensure_seed_data(db)
    db.commit()
    return {
        "users": db.query(User).count(),
        "candidates": db.query(Candidate).count(),
        "assessments": db.query(Assessment).count(),
        "demo_scores": db.query(ScoreRecord).filter(ScoreRecord.is_demo.is_(True)).count(),
    }
