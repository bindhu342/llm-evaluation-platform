from backend.evaluation.base_agent import BaseAgent
from backend.models.schemas import EvaluationRequest


class RelevanceAgent(BaseAgent):
    async def score(self, request: EvaluationRequest) -> dict:
        prompt = (
            "You are an expert evaluator assessing the relevance of an AI-generated response.\n\n"
            "Evaluate whether the response directly and appropriately answers the question asked.\n"
            "Score from 0.0 to 1.0 where:\n"
            "  1.0 = response directly and fully addresses the question\n"
            "  0.5 = response is partially relevant or drifts off-topic\n"
            "  0.0 = response is completely irrelevant to the question\n\n"
            f"Question: {request.question}\n"
            f"Response: {request.response}"
        )
        return await self.generate(prompt)
