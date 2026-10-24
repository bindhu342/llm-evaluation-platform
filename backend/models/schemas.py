from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EvaluationRequest(BaseModel):
    question: str = Field(..., min_length=1)
    response: str = Field(..., min_length=1)
    reference_answer: Optional[str] = None
    source_document: Optional[str] = None


class AgentScores(BaseModel):
    relevance: float = Field(..., ge=0.0, le=1.0)
    accuracy: float = Field(..., ge=0.0, le=1.0)
    hallucination_free: float = Field(..., ge=0.0, le=1.0)
    completeness: float = Field(..., ge=0.0, le=1.0)


class AgentExplanations(BaseModel):
    relevance: str = ""
    accuracy: str = ""
    hallucination_free: str = ""
    completeness: str = ""


class CompletenessAnalysis(BaseModel):
    addressed_aspects: List[str] = Field(default_factory=list)
    missing_aspects: List[str] = Field(default_factory=list)
    explanation: str = ""


class FlaggedClaim(BaseModel):
    claim: str
    reason: str
    evidence: str = ""


class HallucinationAnalysis(BaseModel):
    status: str = "supported"
    flagged_claims: List[FlaggedClaim] = Field(default_factory=list)
    explanation: str = ""


class EvaluationResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    question: str
    response: str

    scores: AgentScores

    explanations: AgentExplanations = Field(
        default_factory=AgentExplanations
    )

    completeness_analysis: CompletenessAnalysis = Field(
        default_factory=CompletenessAnalysis
    )

    final_score: float = Field(..., ge=0.0, le=1.0)
    verdict: str

    hallucination_analysis: Optional[HallucinationAnalysis] = None


# =========================================================
# M3.4 Batch Evaluation Schemas
# =========================================================

class BatchInvalidRow(BaseModel):
    row_number: int
    error: str
    data: dict = Field(default_factory=dict)


class BatchEvaluationItem(BaseModel):
    row_number: int
    evaluation_id: Optional[str] = None
    question: str = ""
    response: str = ""
    result: Optional[EvaluationResult] = None
    status: str
    error: Optional[str] = None


class BatchStatistics(BaseModel):
    average_relevance: float = 0.0
    average_accuracy: float = 0.0
    average_hallucination_free: float = 0.0
    average_completeness: float = 0.0
    average_final_score: float = 0.0

    pass_count: int = 0
    needs_improvement_count: int = 0
    fail_count: int = 0

    hallucination_count: int = 0


class BatchEvaluationResult(BaseModel):
    batch_id: str = Field(default_factory=lambda: str(uuid4()))

    filename: Optional[str] = None

    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0

    completed_rows: int = 0
    failed_rows: int = 0

    status: str = "completed"

    invalid_row_details: List[BatchInvalidRow] = Field(
        default_factory=list
    )

    results: List[BatchEvaluationItem] = Field(
        default_factory=list
    )

    statistics: BatchStatistics = Field(
        default_factory=BatchStatistics
    )


# =========================================================
# Evaluation History
# =========================================================

class HistoryItem(BaseModel):
    id: str
    type: str
    created_at: str

    title: str = ""
    question: Optional[str] = None

    final_score: Optional[float] = None
    verdict: Optional[str] = None

    total_rows: Optional[int] = None
    completed_rows: Optional[int] = None
    failed_rows: Optional[int] = None
    invalid_rows: Optional[int] = None
    average_final_score: Optional[float] = None
    status: Optional[str] = None


class HistoryResponse(BaseModel):
    items: List[HistoryItem] = Field(
        default_factory=list
    )


class HistoryDetail(BaseModel):
    id: str
    type: str
    created_at: str

    evaluation: Optional[EvaluationResult] = None
    batch: Optional[BatchEvaluationResult] = None