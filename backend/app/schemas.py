from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


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
    model_config = ConfigDict(extra="forbid")

    assessment_id: int
    competency_id: str
    score: int = Field(ge=1, le=5)
    explanation: str
    override_reason: Optional[str] = None


class ModerationDecisionInput(BaseModel):
    assessment_id: int
    rationale: str = Field(min_length=10)
    final_scores: dict[str, int]
    override_reasons: dict[str, str] = Field(default_factory=dict)


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
