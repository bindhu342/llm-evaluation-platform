import asyncio

from backend.evaluation.accuracy_agent import AccuracyAgent
from backend.evaluation.completeness_agent import CompletenessAgent
from backend.evaluation.hallucination_agent import HallucinationAgent
from backend.evaluation.relevance_agent import RelevanceAgent
from backend.evaluation.verdict_agent import VerdictAgent

from backend.models.schemas import (
    AgentExplanations,
    AgentScores,
    CompletenessAnalysis,
    EvaluationRequest,
    EvaluationResult,
    HallucinationAnalysis,
)


class Orchestrator:
    def __init__(self):
        self.relevance = RelevanceAgent()
        self.accuracy = AccuracyAgent()
        self.hallucination = HallucinationAgent()
        self.completeness = CompletenessAgent()
        self.verdict = VerdictAgent()

    async def run(
        self,
        request: EvaluationRequest,
    ) -> EvaluationResult:

        (
            relevance_result,
            accuracy_result,
            hallucination_result,
            completeness_result,
        ) = await asyncio.gather(
            self.relevance.score(request),
            self.accuracy.score(request),
            self.hallucination.score(request),
            self.completeness.score(request),
        )

        # ---------------------------------------------------------
        # INDIVIDUAL SCORES
        # ---------------------------------------------------------

        scores = AgentScores(
            relevance=float(relevance_result.get("score", 0.0)),
            accuracy=float(accuracy_result.get("score", 0.0)),
            hallucination_free=float(
                hallucination_result.get("score", 0.0)
            ),
            completeness=float(
                completeness_result.get("score", 0.0)
            ),
        )

        # ---------------------------------------------------------
        # INDIVIDUAL EXPLANATIONS
        # ---------------------------------------------------------

        explanations = AgentExplanations(
            relevance=relevance_result.get(
                "explanation",
                "",
            ),
            accuracy=accuracy_result.get(
                "explanation",
                "",
            ),
            hallucination_free=hallucination_result.get(
                "explanation",
                "",
            ),
            completeness=completeness_result.get(
                "explanation",
                "",
            ),
        )

        # ---------------------------------------------------------
        # COMPLETENESS ANALYSIS
        # ---------------------------------------------------------

        completeness_analysis = CompletenessAnalysis(
            addressed_aspects=completeness_result.get(
                "addressed_aspects",
                [],
            ),
            missing_aspects=completeness_result.get(
                "missing_aspects",
                [],
            ),
            explanation=completeness_result.get(
                "explanation",
                "",
            ),
        )

        # ---------------------------------------------------------
        # HALLUCINATION ANALYSIS
        # ---------------------------------------------------------

        hallucination_analysis = HallucinationAnalysis(
            status=hallucination_result.get(
                "status",
                "supported",
            ),
            flagged_claims=hallucination_result.get(
                "flagged_claims",
                [],
            ),
            explanation=hallucination_result.get(
                "explanation",
                "",
            ),
        )

        # ---------------------------------------------------------
        # FINAL WEIGHTED SCORE + VERDICT
        # ---------------------------------------------------------

        final_score, verdict = self.verdict.evaluate(scores)

        # ---------------------------------------------------------
        # FINAL RESULT
        # ---------------------------------------------------------

        return EvaluationResult(
            question=request.question,
            response=request.response,
            scores=scores,
            explanations=explanations,
            completeness_analysis=completeness_analysis,
            final_score=final_score,
            verdict=verdict,
            hallucination_analysis=hallucination_analysis,
        )