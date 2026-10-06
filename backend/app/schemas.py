from typing import Any, List, Optional

from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class LoginRequest(BaseModel):
    username: str
    password: str


class DeclarationMatch(BaseModel):
    pack_id: str
    title: str
    confidence: float
    skill_gaps: List[str]
    summary: str


class DeclarationResponse(BaseModel):
    matches: List[DeclarationMatch]
    source: str = "sentence embedding + lexical match (demo heuristic)"


class StepCheck(BaseModel):
    step_id: str
    name: str
    status: str
    start_time: float
    end_time: float
    suggested_by_ai: bool = False


class EvidenceMeta(BaseModel):
    title: str
    video_hash: str
    geo: str
    timestamp: str
    hash_chain: str
    live_status: str
    steps: List[StepCheck]


class AssessmentScoreInput(BaseModel):
    assessment_id: int
    competency_id: str
    score: int = Field(ge=1, le=5)
    ai_draft: int = Field(ge=1, le=5)
    explanation: str
    override_reason: Optional[str] = None


class CalibrationMetric(BaseModel):
    metric: str
    value: float
    interpretation: str


class CandidateSummary(BaseModel):
    id: int
    username: str
    name: str
    role: str
    trade: str
    region: str
