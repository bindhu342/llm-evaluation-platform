from backend.evaluation.base_agent import BaseAgent
from backend.models.schemas import EvaluationRequest


class HallucinationAgent(BaseAgent):
    async def score(self, request: EvaluationRequest) -> dict:
        """
        Returns a hallucination_free score:
            1.0 = response is fully supported — no hallucination detected
            0.0 = response is heavily hallucinated or contradicts the reference
        """
        reference = request.source_document or request.reference_answer

        if reference:
            prompt = (
                "You are an expert evaluator detecting hallucinations in AI-generated responses.\n\n"
                "Assess whether the claims in the response are supported by the provided reference.\n"
                "Return a HALLUCINATION-FREE score from 0.0 to 1.0 where:\n"
                "  1.0 = every claim is fully supported by the reference — no hallucination\n"
                "  0.5 = some claims are supported, some are unsupported or fabricated\n"
                "  0.0 = the response contains fabricated or contradicted claims\n\n"
                f"Reference: {reference}\n"
                f"Question: {request.question}\n"
                f"Response: {request.response}"
            )
        else:
            prompt = (
                "You are an expert evaluator detecting hallucinations in AI-generated responses.\n\n"
                "No reference document is provided. Assess whether the response appears grounded.\n"
                "Return a HALLUCINATION-FREE score from 0.0 to 1.0 where:\n"
                "  1.0 = response appears factually grounded with no apparent fabrications\n"
                "  0.5 = response contains some questionable or unverifiable claims\n"
                "  0.0 = response appears to contain fabricated or unsupported claims\n\n"
                f"Question: {request.question}\n"
                f"Response: {request.response}"
            )

        return await self.generate(prompt)
