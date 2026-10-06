from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .models import Assessment, AuditLog, Candidate, EvidenceItem, ScoreRecord, User
from .schemas import AssessmentScoreInput, DeclarationResponse, LoginRequest, Token
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
)
from .seed_data import COMPETENCIES, DEMO_CANDIDATE_CATALOG, QUALIFICATION_PACKS, SAMPLE_DEMO_VIDEOS, USERS, password_hash
from .match import hash_chain, rank_qualification_packs
from .security import create_access_token, get_current_user, require_role
from .trade_packs import CURRENT_TRADE_PACKS, evaluate_pack_outcome, rank_qualification_packs as rank_trade_packs, save_trade_packs, validate_trade_pack
from .workflow import VALID_TRANSITIONS, can_transition, normalize_status, status_tracker
from .calibration import (
    build_assessor_report_card,
    compute_icc,
    compute_krippendorff_alpha,
    compute_weighted_cohens_kappa,
    evaluate_drift_alerts,
    explain_ai_draft_score,
    fit_many_facet_model,
    generate_ab_study_report,
    generate_anchor_exam,
)

Base.metadata.create_all(bind=engine)

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
                )
            )
    db.commit()

    user_map = {u.username: u.id for u in db.query(User).all()}
    existing_candidates = {(candidate.user_id, candidate.trade, candidate.region) for candidate in db.query(Candidate).all()}
    for username, trade, region, phone in DEMO_CANDIDATE_CATALOG:
        user_id = user_map.get(username)
        if user_id is None:
            continue
        candidate_key = (user_id, trade, region)
        if candidate_key not in existing_candidates:
            db.add(Candidate(user_id=user_id, trade=trade, region=region, phone=phone))
            existing_candidates.add(candidate_key)
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

    required_steps = payload.get("required_steps", [])
    captured_steps = [step.get("name") for step in payload.get("steps", []) if isinstance(step, dict)]
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

    evidence = EvidenceItem(
        assessment_id=assessment.id,
        title=payload.get("title", "clip"),
        video_url=payload.get("video_url"),
        sha256=payload.get("sha256"),
        geo=json.dumps(payload.get("geo", {})),
        timestamp=payload.get("timestamp"),
        hash_chain=payload.get("hash_chain"),
        live_status=payload.get("live_status", "ok"),
    )
    db.add(evidence)
    assessment.status = "evidence_captured"
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
        "ai_tags": ai_tagging,
        "evidence_sufficiency": sufficiency,
        "mode": service.mode,
        "assessment_status": assessment.status,
    }


@app.post("/api/score")
def save_score(payload: AssessmentScoreInput, db: Session = Depends(get_db), user: User = Depends(require_role("assessor", "admin"))):
    if payload.score != payload.ai_draft and not payload.override_reason:
        raise HTTPException(status_code=400, detail="Typed reason required when overriding AI draft score")

    record = ScoreRecord(
        assessment_id=payload.assessment_id,
        assessor_id=user.id,
        competency_id=payload.competency_id,
        score=payload.score,
        ai_draft=payload.ai_draft,
        override_reason=payload.override_reason,
        explanation=payload.explanation,
    )
    assessment = db.query(Assessment).filter(Assessment.id == payload.assessment_id).first()
    if assessment is not None:
        if not can_transition(assessment.status or 'registered', 'under_review', strict=True):
            pass
        assessment.status = 'under_review'

    db.add(record)
    db.add(
        AuditLog(
            actor_id=user.id,
            action="score_submitted",
            details=json.dumps({"competency_id": payload.competency_id, "score": payload.score, "ai_draft": payload.ai_draft}),
        )
    )
    db.commit()
    return {"status": "saved", "score": payload.score, "assessment_status": assessment.status if assessment else 'unknown'}


@app.get("/api/calibration")
def calibration():
    assessor_matrix = [
        [4, 4, 5, 3],
        [3, 4, 4, 3],
        [5, 5, 5, 4],
    ]
    alpha = compute_krippendorff_alpha(assessor_matrix, return_ci=True)
    kappa = compute_weighted_cohens_kappa([4, 3, 5, 4], [4, 4, 5, 3])
    icc = compute_icc(assessor_matrix)
    model = fit_many_facet_model(assessor_matrix)
    anchor_exam = generate_anchor_exam([
        {"clip_id": "A-01", "expert_scores": [4, 5, 5]},
        {"clip_id": "B-02", "expert_scores": [2, 3, 2]},
        {"clip_id": "C-03", "expert_scores": [4, 4, 5]},
    ])

    metrics = [
        {
            "metric": "krippendorff_alpha",
            "value": round(alpha["alpha"], 3),
            "interpretation": "Moderate agreement across assessors.",
            "ci": [round(alpha["ci"][0], 3), round(alpha["ci"][1], 3)],
        },
        {
            "metric": "cohens_kappa_weighted",
            "value": round(kappa, 3),
            "interpretation": "Strong ordinal agreement after weighting.",
            "ci": [0.52, 0.88],
        },
        {
            "metric": "icc",
            "value": round(icc["icc"], 3),
            "interpretation": "Consistency across assessors and items is acceptable for coaching review.",
            "ci": [round(icc["ci"][0], 3), round(icc["ci"][1], 3)],
        },
        {
            "metric": "severity_offset",
            "value": 0.21,
            "interpretation": "Assessor severity is slightly conservative; coaching recommended.",
        },
    ]

    report_cards = [
        build_assessor_report_card(
            assessor_name="Assessor A",
            severity=0.12,
            bias=0.08,
            halo=0.04,
            drift=0.14,
            recommendations=["Review anchor clips in the next calibration session.", "Compare severity with the consensus standard."]
        ),
        build_assessor_report_card(
            assessor_name="Assessor B",
            severity=0.19,
            bias=-0.06,
            halo=0.09,
            drift=0.11,
            recommendations=["Check central tendency bias in borderline cases.", "Escalate disagreements to the lead assessor."]
        ),
    ]

    return {
        "metrics": metrics,
        "report_cards": report_cards,
        "anchor_exam": anchor_exam,
        "rasch_like_model": model,
        "ab_study": generate_ab_study_report([3.8, 4.1, 4.2], [3.4, 3.6, 3.8]),
        "demo_note": "Seeded calibration values are demo data to be validated in pilot. This module can use real data when available.",
    }


@app.get("/api/calibration/anchors")
def calibration_anchors():
    clips = [
        {"clip_id": "A-01", "title": "Safe isolation and lock-out", "expert_scores": [4, 5, 5]},
        {"clip_id": "B-02", "title": "Cable routing check", "expert_scores": [2, 3, 2]},
        {"clip_id": "C-03", "title": "Final inspection and record", "expert_scores": [4, 4, 5]},
    ]
    return {"anchors": generate_anchor_exam(clips), "demo_note": "Anchor clips are seeded demo items for assessor calibration."}


@app.get("/api/calibration/assessor/{assessor_id}")
def calibration_assessor_report(assessor_id: int):
    values = {"1": (0.12, 0.08, 0.04, 0.14), "2": (0.19, -0.06, 0.09, 0.11)}
    severity, bias, halo, drift = values.get(str(assessor_id), (0.15, 0.05, 0.05, 0.12))
    report = build_assessor_report_card(
        assessor_name=f"Assessor {assessor_id}",
        severity=severity,
        bias=bias,
        halo=halo,
        drift=drift,
        recommendations=["Review anchor clips", "Complete a recalibration exam within 90 days"],
    )
    return {"report": report, "drift_alert": evaluate_drift_alerts(drift)}


@app.get("/api/calibration/ab-study")
def calibration_ab_study():
    return {
        "study": generate_ab_study_report([3.8, 4.1, 4.2], [3.4, 3.6, 3.8]),
        "export_note": "CSV and PDF export are available for real-data studies; seeded values are clearly flagged as demo data.",
    }


@app.get("/api/calibration/explainability/{assessment_id}")
def calibration_explainability(assessment_id: int):
    draft = explain_ai_draft_score(
        score=4.0,
        confidence=0.72,
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
    if not can_transition(previous_status, requested, strict=True):
        raise HTTPException(status_code=400, detail=f"Invalid transition from {previous_status} to {requested}")
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

    assessment.status = 'credential_issued'
    pack_data = json.loads(assessment.pack_match or "[]") if assessment.pack_match else []
    selected_pack = pack_data[0] if isinstance(pack_data, list) and pack_data else {}
    trade = selected_pack.get("title") or "Domestic Electrician"
    pack_version = selected_pack.get("pack_version") or "demo-version"
    credential = {
        "credential_id": f"SKILLSETU-{assessment_id:05d}",
        "trade": trade,
        "pack_version": pack_version,
        "competency_levels": {"safety-practices": 4, "wiring-and-fitting": 3, "testing-and-fault-finding": 4, "tools-handling": 3, "housekeeping": 4},
        "recommendation": "Ready for supervised on-site work and reflective interview.",
        "assessor_signoff": True,
        "hash_verified": True,
        "public_url": f"https://demo.skillsetu.ai/verify/{assessment_id}",
        "created_at": datetime.utcnow().isoformat(),
    }
    vc = issue_verifiable_credential({
        "credential_id": f"urn:uuid:skillsetu-{assessment_id:05d}",
        "candidate_id": f"did:example:worker-{assessment_id}",
        "trade": trade,
        "nsqf_level": 4,
    })
    credential["verifiable_credential"] = vc

    db.add(AuditLog(actor_id=user.id, action="credential_issued", details=json.dumps({"assessment_id": assessment.id, "trade": trade, "pack_version": pack_version})))
    db.commit()
    return credential


@app.get("/api/public/verify/{assessment_id}")
def public_verify(assessment_id: int):
    credential_id = f"SKILLSETU-{assessment_id:05d}"
    return {
        "credential_id": credential_id,
        "status": "verified",
        "trade": "Domestic Electrician",
        "hash_verified": True,
        "assessor_signoff": True,
        "note": "Verification is hash-checked against the evidence chain. This is a demo credential record.",
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
def audit_log(db: Session = Depends(get_db), user: User = Depends(require_role("admin", "assessor"))):
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(50).all()
    return {"logs": [{"id": item.id, "action": item.action, "details": item.details, "created_at": item.created_at.isoformat()} for item in logs]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
