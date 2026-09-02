import asyncio
from backend.models.schemas import (
    EvaluationRequest, EvaluationResult, AgentScores, AgentExplanations,
)
from backend.evaluation.relevance_agent import RelevanceAgent
from backend.evaluation.accuracy_agent import AccuracyAgent
from backend.evaluation.hallucination_agent import HallucinationAgent
from backend.evaluation.completeness_agent import CompletenessAgent
from backend.evaluation.verdict_agent import VerdictAgent


class Orchestrator:
    def __init__(self):
        self.relevance = RelevanceAgent()
        self.accuracy = AccuracyAgent()
        self.hallucination = HallucinationAgent()
        self.completeness = CompletenessAgent()
        self.verdict = VerdictAgent()

    async def run(self, request: EvaluationRequest) -> EvaluationResult:
        rel, acc, hal, com = await asyncio.gather(
            self.relevance.score(request),
            self.accuracy.score(request),
            self.hallucination.score(request),
            self.completeness.score(request),
        )

        scores = AgentScores(
            relevance=rel["score"],
            accuracy=acc["score"],
            hallucination_free=hal["score"],
            completeness=com["score"],
        )
        explanations = AgentExplanations(
            relevance=rel["explanation"],
            accuracy=acc["explanation"],
            hallucination_free=hal["explanation"],
            completeness=com["explanation"],
        )

        final_score, verdict = self.verdict.evaluate(scores)

        return EvaluationResult(
            question=request.question,
            response=request.response,
            scores=scores,
            explanations=explanations,
            final_score=final_score,
            verdict=verdict,
        )
