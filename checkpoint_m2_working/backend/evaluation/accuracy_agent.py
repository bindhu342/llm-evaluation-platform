from backend.evaluation.base_agent import BaseAgent
from backend.models.schemas import EvaluationRequest


class AccuracyAgent(BaseAgent):
    async def score(self, request: EvaluationRequest) -> dict:
        reference = request.reference_answer or request.source_document

        if reference:
            prompt = (
                "You are an expert evaluator assessing the factual accuracy of an AI-generated response.\n\n"
                "Compare the response against the provided reference. Score from 0.0 to 1.0 where:\n"
                "  1.0 = all facts in the response are correct and consistent with the reference\n"
                "  0.5 = some facts are correct, some are incorrect or missing\n"
                "  0.0 = the response is factually wrong or contradicts the reference\n\n"
                f"Reference: {reference}\n"
                f"Question: {request.question}\n"
                f"Response: {request.response}"
            )
        else:
            prompt = (
                "You are an expert evaluator assessing the factual accuracy of an AI-generated response.\n\n"
                "No reference is provided. Evaluate based on your knowledge. Score from 0.0 to 1.0 where:\n"
                "  1.0 = all facts are correct\n"
                "  0.5 = some facts are correct, some are questionable\n"
                "  0.0 = the response contains clear factual errors\n\n"
                f"Question: {request.question}\n"
                f"Response: {request.response}"
            )

        return await self.generate(prompt)
