from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, index=True, nullable=False)
    full_name = Column(String(120), nullable=False)
    role = Column(String(30), nullable=False, default="worker")
    centre = Column(String(120), nullable=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    trade = Column(String(100), nullable=False)
    region = Column(String(120), nullable=True)
    phone = Column(String(30), nullable=True)
    gender = Column(String(40), nullable=True)
    language = Column(String(40), nullable=True)
    demographics_are_demo = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    status = Column(String(30), default="draft")
    declared_text = Column(Text, nullable=True)
    pack_match = Column(Text, nullable=True)
    review_flagged = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    title = Column(String(120), nullable=False)
    video_url = Column(String(200), nullable=True)
    sha256 = Column(String(128), nullable=True)
    geo = Column(String(200), nullable=True)
    timestamp = Column(String(100), nullable=True)
    hash_chain = Column(Text, nullable=True)
    previous_hash = Column(String(64), nullable=True)
    proof_data = Column(Text, nullable=True)
    live_status = Column(String(40), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class CredentialRecord(Base):
    __tablename__ = "credential_records"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False, unique=True)
    credential_id = Column(String(160), nullable=False, unique=True, index=True)
    credential_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ScoreRecord(Base):
    __tablename__ = "score_records"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    assessor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    competency_id = Column(String(40), nullable=False)
    score = Column(Integer, nullable=False)
    ai_draft = Column(Integer, nullable=True)
    ai_confidence = Column(Float, nullable=True)
    review_round = Column(Integer, nullable=False, default=1)
    ai_assisted = Column(Boolean, nullable=False, default=False)
    is_demo = Column(Boolean, nullable=False, default=False)
    override_reason = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ReviewAssignment(Base):
    __tablename__ = "review_assignments"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False, unique=True)
    assessor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    primary_assessor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(30), nullable=False, default="assigned")
    created_at = Column(DateTime, default=datetime.utcnow)


class ModerationRecord(Base):
    __tablename__ = "moderation_records"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False, unique=True)
    moderator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rationale = Column(Text, nullable=False)
    final_scores = Column(Text, nullable=False)
    overrides = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(120), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
