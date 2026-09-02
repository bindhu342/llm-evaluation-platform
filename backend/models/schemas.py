from pydantic import BaseModel, Field
from typing import Optional
import uuid


class EvaluationRequest(BaseModel):
    question: str = Field(..., min_length=1)
    response: str = Field(..., min_length=1)
    reference_answer: Optional[str] = None
    source_document: Optional[str] = None


class AgentScores(BaseModel):
    relevance: float = Field(ge=0.0, le=1.0)
    accuracy: float = Field(ge=0.0, le=1.0)
    hallucination_free: float = Field(ge=0.0, le=1.0)
    completeness: float = Field(ge=0.0, le=1.0)


class AgentExplanations(BaseModel):
    relevance: str = ""
    accuracy: str = ""
    hallucination_free: str = ""
    completeness: str = ""


class EvaluationResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    response: str
    scores: AgentScores
    explanations: AgentExplanations = Field(default_factory=AgentExplanations)
    final_score: float = Field(ge=0.0, le=1.0)
    verdict: str
