from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime
from datetime import timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .models import Assessment, AuditLog, Candidate, CredentialRecord, EvidenceItem, ModerationRecord, ReviewAssignment, ScoreRecord, User
from .schemas import AssessmentScoreInput, DeclarationResponse, LoginRequest, ModerationDecisionInput, Token
from .ai_services import create_ai_service, evaluate_evidence_sufficiency
from .integrations import (
    build_certificate_pdf,
    build_competency_profile_pdf,
    build_result_csv,
    get_revocations,
    issue_verifiable_credential,
    push_ncvet_result,
    require_api_key,
    verify_verifiable_credential,
    verify_credential_document,
)
from .seed_data import COMPETENCIES, DEMO_CANDIDATE_CATALOG, QUALIFICATION_PACKS, SAMPLE_DEMO_VIDEOS, USERS, password_hash
from .match import hash_chain, rank_qualification_packs
from .evidence_chain import canonical_evidence_json, evidence_chain_hash, verify_evidence_chain
from .security import create_access_token, get_current_user, require_role
from .trade_packs import CURRENT_TRADE_PACKS, evaluate_pack_outcome, rank_qualification_packs as rank_trade_packs, save_trade_packs, validate_trade_pack
from .workflow import VALID_TRANSITIONS, can_transition, normalize_status, status_tracker
from .review_workflow import choose_second_assessor, needs_second_review
from .calibration import (
    build_calibration_summary,
    evaluate_drift_alerts,
    explain_ai_draft_score,
)
from .impact import build_impact_summary
from .demo_reset import reset_demo_state

Base.metadata.create_all(bind=engine)


def ensure_evidence_chain_columns():
    columns = {column["name"] for column in inspect(engine).get_columns("evidence_items")}
    with engine.begin() as connection:
        if "previous_hash" not in columns:
            connection.execute(text("ALTER TABLE evidence_items ADD COLUMN previous_hash VARCHAR(64)"))
        if "proof_data" not in columns:
            connection.execute(text("ALTER TABLE evidence_items ADD COLUMN proof_data TEXT"))

def ensure_review_workflow_columns():
    migrations = {
        "users": {"centre": "VARCHAR(120)"},
        "candidates": {
            "gender": "VARCHAR(40)",
            "language": "VARCHAR(40)",
            "demographics_are_demo": "BOOLEAN NOT NULL DEFAULT 0",
        },
        "assessments": {"review_flagged": "BOOLEAN NOT NULL DEFAULT 0"},
        "score_records": {
            "ai_confidence": "FLOAT",
            "review_round": "INTEGER NOT NULL DEFAULT 1",
            "ai_assisted": "BOOLEAN NOT NULL DEFAULT 0",
            "is_demo": "BOOLEAN NOT NULL DEFAULT 0",
        },
    }
    for table, additions in migrations.items():
        columns = {column["name"] for column in inspect(engine).get_columns(table)}
        with engine.begin() as connection:
            for name, sql_type in additions.items():
                if name not in columns:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))


ensure_evidence_chain_columns()
ensure_review_workflow_columns()

app = FastAPI(title="SkillSetu AI API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def ensure_seed_data(db: Session):
    existing_usernames = {user.username for user in db.query(User).all()}
    for item in USERS:
        if item["username"] not in existing_usernames:
            db.add(
                User(
                    username=item["username"],
                    full_name=item["full_name"],
                    role=item["role"],
                    password_hash=password_hash(item["password"]),
                    centre=f"Centre-{item['username'].removeprefix('assessor')}" if item["role"] == "assessor" else None,
                )
            )
    for assessor_index in range(1, 9):
        assessor = db.query(User).filter(User.username == f"assessor{assessor_index}").first()
        if assessor is not None and not assessor.centre:
            assessor.centre = f"Centre-{assessor_index}"
    db.commit()
    user_map = {u.username: u.id for u in db.query(User).all()}
    existing_candidates = {(candidate.user_id, candidate.trade, candidate.region) for candidate in db.query(Candidate).all()}
    demo_languages = ("Hindi", "English", "Marathi", "Tamil", "Bengali")
    for username, trade, region, phone in DEMO_CANDIDATE_CATALOG:
        user_id = user_map.get(username)
        if user_id is None:
            continue
        candidate_key = (user_id, trade, region)
        if candidate_key not in existing_candidates:
            worker_index = int(username.removeprefix("worker"))
            db.add(Candidate(
                user_id=user_id,
                trade=trade,
                region=region,
                phone=phone,
                gender="woman" if worker_index % 2 == 0 else "man",
                language=demo_languages[(worker_index - 1) % len(demo_languages)],
                demographics_are_demo=True,
            ))
            existing_candidates.add(candidate_key)
        else:
            candidate = db.query(Candidate).filter_by(user_id=user_id, trade=trade, region=region).first()
            if candidate is not None and candidate.gender is None and candidate.language is None:
                worker_index = int(username.removeprefix("worker"))
                candidate.gender = "woman" if worker_index % 2 == 0 else "man"
                candidate.language = demo_languages[(worker_index - 1) % len(demo_languages)]
                candidate.demographics_are_demo = True
    db.commit()
    seed_calibration_records(db)


def create_score_record(
    *,
    assessment_id: int,
    assessor_id: int,
    competency_id: str,
    score: int,
    ai_draft: int | None,
    ai_confidence: float | None,
    review_round: int = 1,
    ai_assisted: bool = False,
    override_reason: str | None = None,
    explanation: str | None = None,
    created_at: datetime | None = None,
    is_demo: bool = False,
) -> ScoreRecord:
    return ScoreRecord(
        assessment_id=assessment_id,
        assessor_id=assessor_id,
        competency_id=competency_id,
        score=score,
        ai_draft=ai_draft,
        ai_confidence=ai_confidence,
        review_round=review_round,
        ai_assisted=ai_assisted,
        is_demo=is_demo,
        override_reason=override_reason,
        explanation=explanation,
        created_at=created_at or datetime.utcnow(),
    )


def seed_calibration_records(db: Session):
    if db.query(ScoreRecord).filter(ScoreRecord.is_demo.is_(True)).first():
        return
    assessors = db.query(User).filter(User.role == "assessor").order_by(User.id.asc()).limit(8).all()
    candidates = db.query(Candidate).order_by(Candidate.id.asc()).limit(60).all()
    if len(assessors) < 8 or len(candidates) < 60:
        return
    severities = [-0.85, -0.55, -0.3, -0.05, 0.18, 0.42, 0.68, 0.92]
    rng = random.Random(20261008)
    anchor_date = datetime(2025, 1, 1)
    for candidate_index, candidate in enumerate(candidates):
        assessment = Assessment(
            candidate_id=candidate.id,
            status="signed_off",
            declared_text=f"DEMO_CALIBRATION_DATA candidate {candidate_index + 1:02d}",
            pack_match="[]",
            created_at=anchor_date + timedelta(days=candidate_index * 5),
        )
        db.add(assessment)
        db.flush()
        month = min(11, candidate_index * 12 // len(candidates))
        for assessor_index, assessor in enumerate(assessors):
            seasonal_drift = 0.0
            if assessor_index == 1 and month >= 9:
                seasonal_drift = 0.85
            elif assessor_index == 6 and month >= 10:
                seasonal_drift = -0.8
            for competency_index, competency in enumerate(COMPETENCIES):
                latent = 3.15 + ((candidate_index * 7 + competency_index * 3) % 17) / 10
                if candidate_index % 6 == 0 and competency_index == 0:
                    latent -= 0.8
                ai_assisted = (candidate_index + assessor_index + competency_index) % 3 != 0
                draft = max(1, min(5, round(latent)))
                noise = rng.gauss(0, 0.38)
                observed = latent - severities[assessor_index] + seasonal_drift + noise
                if ai_assisted:
                    observed = 0.72 * observed + 0.28 * draft
                score = max(1, min(5, round(observed)))
                db.add(create_score_record(
                    assessment_id=assessment.id,
                    assessor_id=assessor.id,
                    competency_id=competency["id"],
                    score=score,
                    ai_draft=draft,
                    ai_confidence=0.68 + 0.03 * (competency_index % 3),
                    ai_assisted=ai_assisted,
                    explanation="Seeded calibration observation; demo data only.",
                    created_at=assessment.created_at + timedelta(minutes=assessor_index * 11 + competency_index),
                    is_demo=True,
                ))
    db.commit()


@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        ensure_seed_data(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "service": "skillsetu-ai"}


def load_calibration_data(db: Session):
    assessor_models = db.query(User).filter(User.role == "assessor").order_by(User.id.asc()).all()
    records = [{
        "assessment_id": record.assessment_id,
        "assessor_id": record.assessor_id,
        "competency_id": record.competency_id,
        "score": record.score,
        "ai_draft": record.ai_draft,
        "ai_assisted": record.ai_assisted,
        "is_demo": record.is_demo,
        "created_at": record.created_at,
    } for record in db.query(ScoreRecord).order_by(ScoreRecord.created_at.asc()).all()]
    assessors = [{"id": assessor.id, "name": assessor.full_name} for assessor in assessor_models]
    return build_calibration_summary(records, assessors), assessor_models


def transition_or_409(assessment: Assessment, target: str, db: Session, actor_id: int):
    current = assessment.status or "registered"
    try:
        allowed = can_transition(current, target, strict=True)
    except ValueError as reason:
        raise HTTPException(status_code=409, detail=str(reason)) from reason
    if not allowed:
        raise HTTPException(status_code=409, detail=f"Invalid transition from {current} to {target}")
    assessment.status = target
    if target != current:
        db.add(AuditLog(
            actor_id=actor_id,
            action="status_transition",
            details=json.dumps({"assessment_id": assessment.id, "from": current, "to": target}),
        ))


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    candidates = db.query(Candidate).count()
    assessments = db.query(Assessment).order_by(Assessment.created_at.asc()).all()
    stage_names = [
        "registered",
        "declared",
        "evidence_captured",
        "under_review",
        "second_review",
        "moderation",
        "signed_off",
        "credential_issued",
        "appeal",
    ]
    stage_counts = {stage: 0 for stage in stage_names}
    for assessment in assessments:
        stage = normalize_status(assessment.status or "registered")
        if stage in stage_counts:
            stage_counts[stage] += 1

    first_assessments = {}
    for assessment in assessments:
        first_assessments.setdefault(assessment.candidate_id, assessment)
    now = datetime.utcnow()
    durations = [
        max(0.0, (now - assessment.created_at).total_seconds())
        for assessment in first_assessments.values()
        if assessment.created_at is not None
    ]
    average_duration = sum(durations) / len(durations) if durations else None
    calibration, _ = load_calibration_data(db)
    alpha_metric = next(metric for metric in calibration["metrics"] if metric["metric"] == "krippendorff_alpha_ordinal")
    candidates_list = db.query(Candidate).all()
    score_records = db.query(ScoreRecord).all()
    impact = build_impact_summary(assessments, candidates_list, score_records)
    return {
        "candidate_count": candidates,
        "assessment_count": len(assessments),
        "assessment_stage_counts": stage_counts,
        "average_time_per_candidate_seconds": round(average_duration) if average_duration is not None else None,
        "krippendorff_alpha": alpha_metric["value"],
        "metrics_are_demo_data": calibration["demo_data"],
        "impact_includes_demo_data": impact["includes_demo_data"],
    }


@app.get("/api/dashboard/impact")
def dashboard_impact(db: Session = Depends(get_db), user: User = Depends(require_role("assessor", "admin", "moderator"))):
    return build_impact_summary(
        db.query(Assessment).order_by(Assessment.created_at.asc()).all(),
        db.query(Candidate).all(),
        db.query(ScoreRecord).order_by(ScoreRecord.created_at.asc()).all(),
    )


@app.post("/api/admin/demo-reset")
def admin_demo_reset(db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    counts = reset_demo_state(db)
    return {
        "reset": True,
        "demo_data": True,
        "message": "Demo state was reset and reseeded. This operation permanently deletes existing demo database rows.",
        **counts,
    }


@app.post("/api/auth/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    from passlib.context import CryptContext
    context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    if not context.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.username})
    return Token(access_token=token, role=user.role, username=user.username)


@app.get("/api/me")
def me(user: User = Depends(get_current_user)):
    return {"username": user.username, "role": user.role, "name": user.full_name}


@app.get("/api/competencies")
def get_competencies():
    return {"competencies": COMPETENCIES, "demo_note": "Rubric descriptors are scenario-anchored and used for assessor scoring; AI never auto-certifies."}


@app.get("/api/trade-packs")
def list_trade_packs():
    return {"trade_packs": CURRENT_TRADE_PACKS, "demo_note": "Trade packs are versioned and human-reviewed; this is a demo registry and not an official certifying dataset."}


@app.post("/api/trade-packs/validate")
def validate_trade_pack_endpoint(payload: dict):
    pack = payload.get("pack") or payload
    validated = validate_trade_pack(pack)
    return validated


@app.post("/api/trade-packs")
def save_trade_pack_endpoint(payload: dict, user: User = Depends(require_role("admin"))):
    packs = payload.get("packs") or payload.get("trade_packs") or []
    if not isinstance(packs, list) or not packs:
        raise HTTPException(status_code=400, detail="Expected a list of trade packs")
    saved = save_trade_packs(packs)
    return {"updated": True, "trade_packs": saved}


@app.post("/api/declare", response_model=DeclarationResponse)
def declare(payload: dict):
    text = payload.get("text", "")
    matches = rank_trade_packs(text, CURRENT_TRADE_PACKS)
    if not matches:
        matches = rank_qualification_packs(text, QUALIFICATION_PACKS)
    return DeclarationResponse(
        matches=[
            {
                "pack_id": item["pack_id"],
                "title": item["title"],
                "confidence": item["confidence"],
                "skill_gaps": item.get("skill_gaps", []),
                "summary": item["summary"],
                "matched_nos": item.get("matched_nos", []),
                "missing_nos": item.get("missing_nos", []),
                "bridge_training": item.get("bridge_training", []),
                "pack_version": item.get("pack_version"),
                "nsqf_level": item.get("nsqf_level"),
            }
            for item in matches
        ],
        source="sentence embedding + rule graph + lexical fallback (demo heuristic)",
    )


@app.get("/api/demo-videos")
def demo_videos():
    return {"videos": SAMPLE_DEMO_VIDEOS}


@app.get("/api/ai-config")
def ai_config():
    service = create_ai_service()
    return {
        "mode": service.mode,
        "label": "Demo data / AI suggested",
        "note": "AI is advisory only and never auto-certifies a worker.",
    }


@app.get("/api/candidates")
def list_candidates(db: Session = Depends(get_db), user: User = Depends(require_role("admin", "assessor"))):
    rows = db.query(Candidate, User).join(User, Candidate.user_id == User.id).all()
    return {
        "candidates": [
            {
                "id": candidate.id,
                "username": user.username,
                "name": user.full_name,
                "trade": candidate.trade,
                "region": candidate.region,
                "role": user.role,
            }
            for candidate, user in rows
        ]
    }


@app.get("/api/assessments")
def list_assessments(db: Session = Depends(get_db), user: User = Depends(require_role("admin", "assessor"))):
    assessments = db.query(Assessment).all()
    return {"assessments": [{"id": a.id, "status": a.status, "declared_text": a.declared_text, "pack_match": a.pack_match} for a in assessments]}


@app.post("/api/assessments")
def create_assessment(payload: dict, db: Session = Depends(get_db), user: User = Depends(require_role("worker", "admin"))):
    candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
    if candidate is None:
        raise HTTPException(status_code=400, detail="Candidate record not found for user")
    matches = payload.get("matches", [])
    if matches and isinstance(matches[0], dict):
        pack_version = matches[0].get("pack_version") or "demo-version"
        selected_pack = {
            "pack_id": matches[0].get("pack_id"),
            "pack_version": pack_version,
            "title": matches[0].get("title"),
            "confidence": matches[0].get("confidence"),
        }
        payload_match = json.dumps([selected_pack])
    else:
        payload_match = json.dumps(matches)
    assessment = Assessment(candidate_id=candidate.id, declared_text=payload.get("text", ""), pack_match=payload_match, status="declared")
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return {"id": assessment.id, "status": assessment.status}


@app.post("/api/evidence")
def save_evidence(payload: dict, db: Session = Depends(get_db), user: User = Depends(require_role("worker", "admin"))):
    candidate = db.query(Candidate).filter(Candidate.user_id == user.id).first()
    if candidate is None:
        raise HTTPException(status_code=400, detail="Candidate record not found")
    assessment = db.query(Assessment).filter(Assessment.candidate_id == candidate.id).order_by(Assessment.id.desc()).first()
    if assessment is None:
        raise HTTPException(status_code=404, detail="No assessment found")
    if assessment.status not in {"declared", "evidence_captured"}:
        raise HTTPException(status_code=409, detail=f"Evidence cannot be added while assessment is {assessment.status}")

    required_steps = payload.get("required_steps", [])
    captured_steps = [
        step.get("name")
        for step in payload.get("steps", [])
        if isinstance(step, dict) and step.get("status") == "done"
    ]
    quality = payload.get("quality", {})
    sufficiency = evaluate_evidence_sufficiency(
        required_steps=required_steps,
        captured_steps=captured_steps,
        brightness=quality.get("brightness"),
        blur=quality.get("blur"),
        is_blurry=bool(quality.get("is_blurry")),
    )
    service = create_ai_service()
    ai_tagging = service.analyze_steps([step.get("name") for step in payload.get("steps", []) if isinstance(step, dict)])

    video_hash = payload.get("sha256") or payload.get("video_hash")
    if not isinstance(video_hash, str) or len(video_hash) != 64 or any(character not in "0123456789abcdefABCDEF" for character in video_hash):
        raise HTTPException(status_code=422, detail="A SHA-256 video hash is required")
    timestamp = payload.get("timestamp")
    if not isinstance(timestamp, str) or not timestamp:
        raise HTTPException(status_code=422, detail="An evidence timestamp is required")
    geo = payload.get("geo")
    evidence_proof = {
        "video_sha256": video_hash.lower(),
        "geo": geo if isinstance(geo, dict) else {},
        "timestamp": timestamp,
        "liveness": payload.get("liveness", {}),
        "steps": payload.get("steps", []),
        "quality": payload.get("quality", {}),
        "vision_mode": payload.get("vision_mode", "unknown"),
    }
    previous_evidence = db.query(EvidenceItem).order_by(EvidenceItem.id.desc()).first()
    previous_hash = previous_evidence.hash_chain if previous_evidence and previous_evidence.hash_chain else ""
    chain_hash = evidence_chain_hash(previous_hash, evidence_proof)
    evidence = EvidenceItem(
        assessment_id=assessment.id,
        title=payload.get("title", "clip"),
        video_url=payload.get("video_url"),
        sha256=video_hash.lower(),
        geo=json.dumps(evidence_proof["geo"], sort_keys=True),
        timestamp=timestamp,
        hash_chain=chain_hash,
        previous_hash=previous_hash,
        proof_data=canonical_evidence_json(evidence_proof),
        live_status=payload.get("live_status", "ok"),
    )
    db.add(evidence)
    if assessment.status == "declared":
        transition_or_409(assessment, "evidence_captured", db, user.id)
    assessment.review_flagged = not sufficiency["sufficient"]
    db.add(
        AuditLog(
            actor_id=user.id,
            action="evidence_submitted",
            details=json.dumps({"title": evidence.title, "sufficiency": sufficiency, "ai_mode": service.mode}),
        )
    )
    db.commit()
    return {
        "id": evidence.id,
        "verified": True,
        "hash_chain": chain_hash,
        "ai_tags": ai_tagging,
        "evidence_sufficiency": sufficiency,
        "mode": service.mode,
        "assessment_status": assessment.status,
    }


@app.post("/api/evidence/verify-chain")
def verify_evidence_chain_endpoint(db: Session = Depends(get_db), user: User = Depends(require_role("worker", "assessor", "moderator", "admin"))):
    return _verify_saved_evidence_chain(db)


def _verify_saved_evidence_chain(db: Session):
    evidence_items = db.query(EvidenceItem).order_by(EvidenceItem.id.asc()).all()
    entries = []
    for item in evidence_items:
        try:
            proof_data = json.loads(item.proof_data) if item.proof_data else None
        except json.JSONDecodeError:
            proof_data = None
        if proof_data is not None:
            try:
                stored_geo = json.loads(item.geo or "{}")
            except json.JSONDecodeError:
                stored_geo = None
            if (
                proof_data.get("video_sha256") != item.sha256
                or proof_data.get("timestamp") != item.timestamp
                or proof_data.get("geo") != stored_geo
            ):
                proof_data = None
        entries.append({
            "id": item.id,
            "proof_data": proof_data,
            "previous_hash": item.previous_hash,
            "hash_chain": item.hash_chain,
        })
    results = verify_evidence_chain(entries)
    verified_count = sum(1 for result in results if result["valid"])
    return {
        "valid": verified_count == len(evidence_items),
        "verified_count": verified_count,
        "total_count": len(evidence_items),
        "broken_links": [result for result in results if not result["valid"]],
        "results": results,
    }


@app.post("/api/evidence/simulate-tampering")
def simulate_evidence_tampering(db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    worker = db.query(User).filter(User.username == "worker1").first()
    candidate = db.query(Candidate).filter(Candidate.user_id == worker.id).first() if worker else None
    if candidate is None:
        raise HTTPException(status_code=409, detail="Seeded demo worker is unavailable; reset or seed the demo data first")

    assessment = Assessment(
        candidate_id=candidate.id,
        status="evidence_captured",
        declared_text="DEMO_TAMPER_DEMO_ONLY",
        pack_match="[]",
    )
    db.add(assessment)
    db.flush()
    proof = {
        "video_sha256": "0" * 64,
        "geo": {},
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "liveness": {"result": "not-run", "simulated_demo": True},
        "steps": [],
        "quality": {},
        "vision_mode": "tamper-demo-only",
    }
    previous_evidence = db.query(EvidenceItem).order_by(EvidenceItem.id.desc()).first()
    previous_hash = previous_evidence.hash_chain if previous_evidence and previous_evidence.hash_chain else ""
    item = EvidenceItem(
        assessment_id=assessment.id,
        title="DEMO ONLY — simulated evidence tamper",
        sha256=proof["video_sha256"],
        geo="{}",
        timestamp=proof["timestamp"],
        previous_hash=previous_hash,
        hash_chain=evidence_chain_hash(previous_hash, proof),
        proof_data=canonical_evidence_json(proof),
        live_status="simulated",
    )
    db.add(item)
    db.flush()
    db.commit()
    edited_proof = {**proof, "tamper_demo_marker": "stored record edited for presentation demo"}
    item.proof_data = canonical_evidence_json(edited_proof)
    db.add(AuditLog(
        actor_id=user.id,
        action="demo_evidence_tampered",
        details=json.dumps({"evidence_id": item.id, "assessment_id": assessment.id, "demo_only": True}),
    ))
    db.commit()
    return {
        "evidence_id": item.id,
        "assessment_id": assessment.id,
        "simulated": True,
        "message": "A clearly labeled demo evidence record was altered. Verification should now report a broken link; reset the demo database to restore the chain.",
    }


@app.post("/api/score")
def save_score(payload: AssessmentScoreInput, db: Session = Depends(get_db), user: User = Depends(require_role("assessor", "admin"))):
    assessment = db.query(Assessment).filter(Assessment.id == payload.assessment_id).first()
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if payload.competency_id not in {item["id"] for item in COMPETENCIES}:
        raise HTTPException(status_code=422, detail="Unknown competency")
    if assessment.status not in {"declared", "evidence_captured", "under_review", "second_review"}:
        raise HTTPException(status_code=409, detail=f"Assessment cannot be scored while {assessment.status}")

    assignment = db.query(ReviewAssignment).filter(ReviewAssignment.assessment_id == assessment.id).first()
    primary_records = db.query(ScoreRecord).filter(
        ScoreRecord.assessment_id == assessment.id,
        ScoreRecord.review_round == 1,
    ).order_by(ScoreRecord.id.asc()).all()
    primary_assessor_id = assignment.primary_assessor_id if assignment else (primary_records[0].assessor_id if primary_records else user.id)
    if assignment and user.id == assignment.assessor_id:
        review_round = 2
    elif user.id == primary_assessor_id:
        review_round = 1
    else:
        raise HTTPException(status_code=403, detail="This assessment is assigned to a different assessor")
    if db.query(ScoreRecord).filter_by(
        assessment_id=assessment.id,
        assessor_id=user.id,
        competency_id=payload.competency_id,
    ).first():
        raise HTTPException(status_code=409, detail="You have already submitted this competency score")

    ai_draft = 3 if assessment.review_flagged else 4
    ai_confidence = 0.55 if assessment.review_flagged else 0.8
    if payload.score != ai_draft and not (payload.override_reason or "").strip():
        raise HTTPException(status_code=400, detail="Typed reason required when overriding the AI draft score")

    new_assignment = None
    if assignment is None and not primary_records and needs_second_review(
        flagged=assessment.review_flagged,
        confidence=ai_confidence,
    ):
        assessors = db.query(User).filter(User.role == "assessor").all()
        reviewer = choose_second_assessor(assessors, user.id, user.centre)
        if reviewer is None:
            raise HTTPException(status_code=409, detail="No second assessor is available at a different centre")
        new_assignment = ReviewAssignment(
            assessment_id=assessment.id,
            assessor_id=reviewer.id,
            primary_assessor_id=user.id,
        )

    if assessment.status in {"declared", "evidence_captured"}:
        transition_or_409(assessment, "under_review", db, user.id)
    record = create_score_record(
        assessment_id=assessment.id,
        assessor_id=user.id,
        competency_id=payload.competency_id,
        score=payload.score,
        ai_draft=ai_draft,
        ai_confidence=ai_confidence,
        review_round=review_round,
        ai_assisted=False,
        override_reason=payload.override_reason,
        explanation=payload.explanation,
    )
    db.add(record)
    if new_assignment is not None:
        db.add(new_assignment)
        db.flush()
        transition_or_409(assessment, "second_review", db, user.id)
        db.add(AuditLog(actor_id=user.id, action="second_review_assigned", details=json.dumps({
            "assessment_id": assessment.id,
            "primary_assessor_id": user.id,
            "second_assessor_id": new_assignment.assessor_id,
            "second_assessor_centre": db.query(User).filter(User.id == new_assignment.assessor_id).one().centre,
        })))
    db.add(AuditLog(actor_id=user.id, action="score_submitted", details=json.dumps({
        "assessment_id": assessment.id,
        "competency_id": payload.competency_id,
        "score": payload.score,
        "review_round": review_round,
        "override_reason": payload.override_reason,
    })))
    db.flush()

    if assignment or new_assignment:
        assignment = assignment or new_assignment
        scores = db.query(ScoreRecord).filter(ScoreRecord.assessment_id == assessment.id).all()
        primary = {item.competency_id: item for item in scores if item.review_round == 1}
        secondary = {item.competency_id: item for item in scores if item.review_round == 2}
        expected = {item["id"] for item in COMPETENCIES}
        if expected.issubset(primary) and expected.issubset(secondary):
            disagreements = {
                competency_id: abs(primary[competency_id].score - secondary[competency_id].score)
                for competency_id in expected
            }
            if any(difference >= 2 for difference in disagreements.values()):
                transition_or_409(assessment, "moderation", db, user.id)
                assignment.status = "moderation"
                db.add(AuditLog(actor_id=user.id, action="moderation_escalated", details=json.dumps({
                    "assessment_id": assessment.id,
                    "competency_differences": disagreements,
                })))
            else:
                transition_or_409(assessment, "signed_off", db, user.id)
                assignment.status = "completed"
    else:
        primary_scores = {item.competency_id for item in db.query(ScoreRecord).filter_by(
            assessment_id=assessment.id, review_round=1,
        ).all()}
        if {item["id"] for item in COMPETENCIES}.issubset(primary_scores):
            transition_or_409(assessment, "signed_off", db, user.id)
    db.commit()
    return {
        "status": "saved",
        "score": payload.score,
        "ai_draft": ai_draft,
        "assessment_status": assessment.status,
        "review_round": review_round,
        "second_review_assigned": assignment is not None,
        "assigned_assessor_id": assignment.assessor_id if assignment else None,
    }


@app.get("/api/reviews/queue")
def review_queue(db: Session = Depends(get_db), user: User = Depends(require_role("assessor"))):
    assignments = db.query(ReviewAssignment).filter(
        ReviewAssignment.assessor_id == user.id,
        ReviewAssignment.status == "assigned",
    ).order_by(ReviewAssignment.created_at.asc()).all()
    return {"assignments": [{
        "assessment_id": item.assessment_id,
        "status": item.status,
        "centre": db.query(User).filter(User.id == item.primary_assessor_id).one().centre,
    } for item in assignments]}


@app.get("/api/moderation/queue")
def moderation_queue(db: Session = Depends(get_db), user: User = Depends(require_role("moderator"))):
    assessments = db.query(Assessment).filter(Assessment.status == "moderation").order_by(Assessment.id.asc()).all()
    return {"assessments": [{"assessment_id": item.id, "status": item.status} for item in assessments]}


@app.get("/api/assessments/{assessment_id}/review")
def assessment_review(assessment_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("assessor", "moderator", "admin"))):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    scores = db.query(ScoreRecord).filter(ScoreRecord.assessment_id == assessment_id).order_by(ScoreRecord.id.asc()).all()
    assignment = db.query(ReviewAssignment).filter(ReviewAssignment.assessment_id == assessment_id).first()
    if user.role == "moderator" or user.role == "admin":
        moderation = db.query(ModerationRecord).filter_by(assessment_id=assessment_id).first()
        if user.role == "moderator" and assessment.status != "moderation" and moderation is None:
            raise HTTPException(status_code=403, detail="Blind scores and AI drafts are visible only during moderation")
        return {
            "assessment_id": assessment_id,
            "status": assessment.status,
            "assignment": {"assessor_id": assignment.assessor_id, "primary_assessor_id": assignment.primary_assessor_id} if assignment else None,
            "moderation": {
                "rationale": moderation.rationale,
                "final_scores": json.loads(moderation.final_scores),
                "overrides": json.loads(moderation.overrides),
            } if moderation else None,
            "scores": [{
                "assessor_id": score.assessor_id,
                "review_round": score.review_round,
                "competency_id": score.competency_id,
                "score": score.score,
                "ai_draft": score.ai_draft,
                "ai_confidence": score.ai_confidence,
                "override_reason": score.override_reason,
                "explanation": score.explanation,
            } for score in scores],
        }
    is_assigned_reviewer = assignment is not None and assignment.assessor_id == user.id
    is_primary = assignment is not None and assignment.primary_assessor_id == user.id
    is_existing_assessor = any(score.assessor_id == user.id for score in scores)
    is_unstarted = not assignment and not scores
    if not (is_assigned_reviewer or is_primary or is_existing_assessor or is_unstarted):
        raise HTTPException(status_code=403, detail="This assessment is not assigned to you")
    return {
        "assessment_id": assessment_id,
        "status": assessment.status,
        "review_round": 2 if is_assigned_reviewer else 1,
        "scores": [{
            "competency_id": score.competency_id,
            "score": score.score,
            "ai_draft": score.ai_draft,
            "review_round": score.review_round,
        } for score in scores if score.assessor_id == user.id],
    }


@app.post("/api/moderation")
def save_moderation(payload: ModerationDecisionInput, db: Session = Depends(get_db), user: User = Depends(require_role("moderator"))):
    assessment = db.query(Assessment).filter(Assessment.id == payload.assessment_id).first()
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if assessment.status != "moderation":
        raise HTTPException(status_code=409, detail="Assessment is not awaiting moderation")
    if db.query(ModerationRecord).filter_by(assessment_id=assessment.id).first():
        raise HTTPException(status_code=409, detail="A moderation decision has already been recorded")
    competency_ids = {item["id"] for item in COMPETENCIES}
    if set(payload.final_scores) != competency_ids or any(score < 1 or score > 5 for score in payload.final_scores.values()):
        raise HTTPException(status_code=422, detail="A final score from 1 to 5 is required for each competency")
    score_records = db.query(ScoreRecord).filter(ScoreRecord.assessment_id == assessment.id).all()
    by_competency: dict[str, list[ScoreRecord]] = {}
    for score in score_records:
        by_competency.setdefault(score.competency_id, []).append(score)
    overrides = {}
    for competency_id, final_score in payload.final_scores.items():
        paired = by_competency.get(competency_id, [])
        if len(paired) < 2:
            raise HTTPException(status_code=409, detail=f"Both assessor scores are required for {competency_id}")
        if any(final_score != score.score for score in paired):
            reason = (payload.override_reasons.get(competency_id) or "").strip()
            if not reason:
                raise HTTPException(status_code=400, detail=f"An override reason is required for {competency_id}")
            overrides[competency_id] = {"final_score": final_score, "reason": reason}
    decision = ModerationRecord(
        assessment_id=assessment.id,
        moderator_id=user.id,
        rationale=payload.rationale.strip(),
        final_scores=json.dumps(payload.final_scores, sort_keys=True),
        overrides=json.dumps(overrides, sort_keys=True),
    )
    db.add(decision)
    previous_status = assessment.status
    if not can_transition(previous_status, "signed_off", strict=True):
        raise HTTPException(status_code=409, detail=f"Invalid transition from {previous_status} to signed_off")
    transition_or_409(assessment, "signed_off", db, user.id)
    assignment = db.query(ReviewAssignment).filter_by(assessment_id=assessment.id).first()
    if assignment:
        assignment.status = "completed"
    db.add(AuditLog(actor_id=user.id, action="moderation_decision", details=json.dumps({
        "assessment_id": assessment.id,
        "rationale": decision.rationale,
        "final_scores": payload.final_scores,
        "overrides": overrides,
    })))
    db.commit()
    return {"assessment_id": assessment.id, "status": assessment.status, "moderation_id": decision.id, "overrides": overrides}


@app.get("/api/calibration")
def calibration(db: Session = Depends(get_db), user: User = Depends(require_role("assessor", "admin"))):
    summary, _ = load_calibration_data(db)
    if user.role == "assessor":
        summary["report_cards"] = [
            report for report in summary["report_cards"] if report["assessor_name"] == user.full_name
        ]
    summary["data_label"] = "demo data" if summary["demo_data"] else (
        "includes demo data" if summary["includes_demo_data"] else "stored assessment data"
    )
    summary["viewer"] = {"role": user.role, "report_is_private": user.role == "assessor"}
    return summary


@app.get("/api/calibration/anchors")
def calibration_anchors(db: Session = Depends(get_db), user: User = Depends(require_role("assessor", "admin"))):
    summary, _ = load_calibration_data(db)
    return {"anchors": summary["anchor_clips"], "demo_data": summary["demo_data"]}


@app.get("/api/calibration/assessor/{assessor_id}")
def calibration_assessor_report(assessor_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("assessor", "admin"))):
    target = db.query(User).filter(User.id == assessor_id, User.role == "assessor").first()
    if target is None:
        raise HTTPException(status_code=404, detail="Assessor not found")
    if user.role == "assessor" and target.id != user.id:
        raise HTTPException(status_code=403, detail="Assessor coaching reports are private")
    summary, _ = load_calibration_data(db)
    report = next((item for item in summary["report_cards"] if item["assessor_name"] == target.full_name), None)
    if report is None:
        raise HTTPException(status_code=404, detail="No stored scores are available for this assessor")
    report["recommended_anchor_clips"] = summary["anchor_clips"]
    return {"report": report, "drift_alert": evaluate_drift_alerts(report["drift"], threshold=0.5), "demo_data": summary["demo_data"]}


@app.get("/api/calibration/my-report")
def my_calibration_report(db: Session = Depends(get_db), user: User = Depends(require_role("assessor"))):
    summary, _ = load_calibration_data(db)
    report = next((item for item in summary["report_cards"] if item["assessor_name"] == user.full_name), None)
    if report is None:
        raise HTTPException(status_code=404, detail="No stored scores are available for your coaching report")
    report["recommended_anchor_clips"] = summary["anchor_clips"]
    return {"report": report, "drift_alert": evaluate_drift_alerts(report["drift"], threshold=0.5), "demo_data": summary["demo_data"]}


@app.get("/api/calibration/ab-study")
def calibration_ab_study(db: Session = Depends(get_db), user: User = Depends(require_role("assessor", "admin"))):
    summary, _ = load_calibration_data(db)
    return {"comparison": summary["assistance_comparison"], "demo_data": summary["demo_data"]}


@app.get("/api/calibration/explainability/{assessment_id}")
def calibration_explainability(assessment_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("assessor", "moderator", "admin"))):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    record_query = db.query(ScoreRecord).filter(ScoreRecord.assessment_id == assessment_id)
    if user.role == "assessor":
        record_query = record_query.filter(ScoreRecord.assessor_id == user.id)
    elif user.role == "moderator" and assessment.status != "moderation":
        raise HTTPException(status_code=403, detail="AI drafts are visible to moderators only during moderation")
    record = record_query.order_by(ScoreRecord.id.desc()).first()
    if record is None:
        raise HTTPException(status_code=403, detail="Submit your own score before viewing the AI draft")
    draft = explain_ai_draft_score(
        score=float(record.ai_draft),
        confidence=record.ai_confidence or 0.0,
        factors=["rubric anchor alignment", "clip clarity", "step completion", "safety-critical checks"],
    )
    return {
        "assessment_id": assessment_id,
        "ai_score": draft,
        "explanation": "The AI draft score is shown with the evidence clips, rubric anchors, and confidence. It is advisory-only and cannot certify the worker without assessor sign-off.",
    }


@app.patch("/api/assessments/{assessment_id}/status")
def update_assessment_status(assessment_id: int, payload: dict, db: Session = Depends(get_db), user: User = Depends(require_role("assessor", "admin", "moderator"))):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    previous_status = assessment.status or 'registered'
    requested = normalize_status(payload.get("status") or assessment.status)
    try:
        allowed = can_transition(previous_status, requested, strict=True)
    except ValueError as reason:
        raise HTTPException(status_code=400, detail=str(reason)) from reason
    if not allowed:
        raise HTTPException(status_code=400, detail=f"Invalid transition from {previous_status} to {requested}")
    if requested != previous_status:
        assignment = db.query(ReviewAssignment).filter_by(assessment_id=assessment.id).first()
        scores = db.query(ScoreRecord).filter_by(assessment_id=assessment.id).all()
        primary = {item.competency_id: item for item in scores if item.review_round == 1}
        secondary = {item.competency_id: item for item in scores if item.review_round == 2}
        expected = {item["id"] for item in COMPETENCIES}
        if requested == "second_review" and (assignment is None or assignment.status != "assigned"):
            raise HTTPException(status_code=409, detail="Second review requires an active reviewer assignment")
        if requested == "moderation":
            differences = [
                abs(primary[key].score - secondary[key].score)
                for key in expected
                if key in primary and key in secondary
            ]
            if not expected.issubset(primary) or not expected.issubset(secondary) or max(differences, default=0) < 2:
                raise HTTPException(status_code=409, detail="Moderation requires complete independent scores with a 2-point disagreement")
        if requested == "signed_off":
            moderated = db.query(ModerationRecord).filter_by(assessment_id=assessment.id).first()
            if previous_status == "moderation":
                if moderated is None:
                    raise HTTPException(status_code=409, detail="A moderator decision is required before sign-off")
            elif assignment and assignment.status != "completed":
                raise HTTPException(status_code=409, detail="Second review must be completed before sign-off")
            elif not assignment and not expected.issubset(primary):
                raise HTTPException(status_code=409, detail="All competency scores are required before sign-off")
    assessment.status = requested
    db.add(AuditLog(actor_id=user.id, action="status_transition", details=json.dumps({"from": previous_status, "to": requested, "actor_role": user.role})))
    db.commit()
    return {"assessment_id": assessment.id, "status": assessment.status, "allowed_next": VALID_TRANSITIONS.get(requested, [])}


@app.get("/api/assessments/{assessment_id}/status")
def get_assessment_status(assessment_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("worker", "assessor", "admin", "moderator"))):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return {"assessment_id": assessment.id, "status": assessment.status, "tracker": status_tracker(), "allowed_next": VALID_TRANSITIONS.get(assessment.status or 'registered', [])}


@app.get("/api/certificate/{assessment_id}")
def certificate(assessment_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("assessor", "admin"))):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    stored = db.query(CredentialRecord).filter_by(assessment_id=assessment_id).first()
    if stored is None and assessment.status not in {"signed_off", "credential_issued"}:
        raise HTTPException(status_code=409, detail="Assessment must be signed off before credential issuance")

    if stored is None:
        candidate = db.query(Candidate).filter_by(id=assessment.candidate_id).first()
        pack_data = json.loads(assessment.pack_match or "[]") if assessment.pack_match else []
        selected_pack = pack_data[0] if isinstance(pack_data, list) and pack_data else {}
        trade = candidate.trade if candidate else (selected_pack.get("title") or "Unknown trade")
        pack_version = selected_pack.get("pack_version") or selected_pack.get("version") or "demo-version"
        credential_id = f"urn:uuid:skillsetu-{assessment_id:05d}"
        credential = issue_verifiable_credential({
            "credential_id": credential_id,
            "candidate_id": f"did:example:worker-{candidate.user_id if candidate else assessment.candidate_id}",
            "trade": trade,
            "nsqf_level": selected_pack.get("nsqf_level") or 4,
        })
        stored = CredentialRecord(
            assessment_id=assessment_id,
            credential_id=credential_id,
            credential_json=json.dumps(credential, sort_keys=True),
        )
        db.add(stored)
        if assessment.status == "signed_off":
            transition_or_409(assessment, "credential_issued", db, user.id)
        db.add(AuditLog(actor_id=user.id, action="credential_issued", details=json.dumps({
            "assessment_id": assessment.id,
            "trade": trade,
            "pack_version": pack_version,
            "signature_type": credential["proof"]["type"],
            "demo_credential": True,
        })))
        db.commit()
    else:
        credential = json.loads(stored.credential_json)

    verification = verify_credential_document(credential)
    chain_check = _verify_saved_evidence_chain(db)
    evidence_chain_verified = chain_check["valid"] and db.query(EvidenceItem).filter_by(assessment_id=assessment_id).count() > 0
    return {
        "assessment_id": assessment_id,
        "credential_id": f"SKILLSETU-{assessment_id:05d}",
        "trade": credential["credentialSubject"]["trade"],
        "assessor_signoff": True,
        "signature_verified": verification["signature_verified"],
        "hash_verified": verification["hash_verified"],
        "verified": verification["valid"] and evidence_chain_verified and assessment.status == "credential_issued",
        "evidence_chain_verified": evidence_chain_verified,
        "public_url": f"/verify/{assessment_id}",
        "created_at": credential["issuanceDate"],
        "verifiable_credential": credential,
        "demo_data": bool(assessment.declared_text and assessment.declared_text.startswith("DEMO_CALIBRATION_DATA")),
    }


@app.get("/api/public/verify/{assessment_id}")
def public_verify(assessment_id: int, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter_by(id=assessment_id).first()
    stored = db.query(CredentialRecord).filter_by(assessment_id=assessment_id).first()
    if assessment is None or stored is None:
        return {
            "credential_id": f"SKILLSETU-{assessment_id:05d}",
            "status": "not_found",
            "verified": False,
            "signature_verified": False,
            "hash_verified": False,
            "evidence_chain_verified": False,
            "assessor_signoff": False,
            "note": "No issued credential record exists for this assessment.",
        }
    credential = json.loads(stored.credential_json)
    signature_check = verify_credential_document(credential)
    chain_check = _verify_saved_evidence_chain(db)
    assessment_evidence = db.query(EvidenceItem).filter_by(assessment_id=assessment_id).count()
    evidence_chain_verified = chain_check["valid"] and assessment_evidence > 0
    verified = (
        signature_check["valid"]
        and evidence_chain_verified
        and assessment.status == "credential_issued"
    )
    return {
        "credential_id": f"SKILLSETU-{assessment_id:05d}",
        "status": "verified" if verified else "failed",
        "verified": verified,
        "trade": credential["credentialSubject"]["trade"],
        "hash_verified": signature_check["hash_verified"],
        "signature_verified": signature_check["signature_verified"],
        "evidence_chain_verified": evidence_chain_verified,
        "assessor_signoff": assessment.status in {"signed_off", "credential_issued"},
        "note": "Demo-issued credential. The Ed25519 signature and the full evidence chain are checked at verification time; this is not an accredited credential.",
        "demo_data": bool(assessment.declared_text and assessment.declared_text.startswith("DEMO_CALIBRATION_DATA")),
    }


@app.post("/api/integrations/vc/issue")
def issue_vc_endpoint(payload: dict, _: str = Depends(require_api_key)):
    credential = issue_verifiable_credential(payload)
    return {"status": "issued", "credential_id": credential["id"], "credential": credential}


@app.get("/api/public/vc/verify/{credential_id}")
def public_vc_verify(credential_id: str):
    return verify_verifiable_credential(credential_id)


@app.get("/api/integrations/revocations")
def revocations(_: str = Depends(require_api_key)):
    return get_revocations()


@app.post("/api/integrations/ncvet/push", status_code=202)
def ncvet_push(payload: dict, _: str = Depends(require_api_key)):
    return push_ncvet_result(payload)


@app.get("/api/integrations/exports/csv")
def export_csv(_: str = Depends(require_api_key)):
    csv_payload = build_result_csv()
    return Response(content=csv_payload, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=skillsetu-results.csv"})


@app.get("/api/integrations/exports/certificate/{assessment_id}")
def export_certificate_pdf(assessment_id: int, _: str = Depends(require_api_key)):
    pdf_bytes = build_certificate_pdf(assessment_id)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=certificate-{assessment_id}.pdf"})


@app.get("/api/integrations/exports/competency-profile/{assessment_id}")
def export_competency_profile(assessment_id: int, _: str = Depends(require_api_key)):
    pdf_bytes = build_competency_profile_pdf(assessment_id)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=competency-profile-{assessment_id}.pdf"})


@app.get("/api/audit")
def audit_log(db: Session = Depends(get_db), user: User = Depends(require_role("admin", "assessor", "moderator"))):
    query = db.query(AuditLog)
    if user.role == "assessor":
        query = query.filter(AuditLog.actor_id == user.id)
    elif user.role == "moderator":
        query = query.filter(AuditLog.action != "score_submitted")
    logs = query.order_by(AuditLog.id.desc()).limit(50).all()
    return {"logs": [{"id": item.id, "action": item.action, "details": item.details, "created_at": item.created_at.isoformat()} for item in logs]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
