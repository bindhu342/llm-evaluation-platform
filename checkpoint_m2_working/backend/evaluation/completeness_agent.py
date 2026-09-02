from backend.evaluation.base_agent import BaseAgent
from backend.models.schemas import EvaluationRequest


class CompletenessAgent(BaseAgent):
    async def score(self, request: EvaluationRequest) -> dict:
        prompt = (
            "You are an expert evaluator assessing the completeness of an AI-generated response.\n\n"
            "Determine whether the response sufficiently covers all aspects of the question.\n"
            "Score from 0.0 to 1.0 where:\n"
            "  1.0 = response fully addresses all parts of the question\n"
            "  0.5 = response addresses some but not all parts of the question\n"
            "  0.0 = response is incomplete or only superficially answers the question\n\n"
            f"Question: {request.question}\n"
            f"Response: {request.response}"
        )
        return await self.generate(prompt)
