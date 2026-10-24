from backend.evaluation.base_agent import BaseAgent
from backend.models.schemas import EvaluationRequest


class CompletenessAgent(BaseAgent):
    async def score(self, request: EvaluationRequest) -> dict:
        prompt = f"""
You are an expert completeness judge for an AI response evaluation system.

Your task is to evaluate ONLY whether the AI response covers the
requirements of the question.

IMPORTANT RULES:
- Judge completeness/coverage only.
- Do NOT judge factual correctness.
- Do NOT penalize completeness because a statement is false or hallucinated.
- Accuracy and hallucination are evaluated separately.
- First identify the important aspects, requirements, or sub-questions
  requested by the question.
- Determine which of those aspects are addressed by the response.
- Put every clearly addressed requirement into addressed_aspects.
- Put every missing or insufficiently addressed requirement into
  missing_aspects.
- Do not leave both arrays empty when the question contains a clear
  requirement.
- For a simple one-part question, the main requirement should appear
  in addressed_aspects if the response attempts to answer it.
- If the response does not answer the requirement, put it in
  missing_aspects.
- Do not invent requirements that are not reasonably implied by the question.

SCORING SCALE:
1.0 = All important aspects are addressed sufficiently.
0.75 = Main question is answered with only minor missing details.
0.50 = Some important aspects are addressed but significant information
       is missing.
0.25 = Very little of the requested information is addressed.
0.0 = The response does not meaningfully address the question.

Return ONLY valid JSON.

The JSON MUST contain exactly these four fields:

{{
    "score": 1.0,
    "addressed_aspects": [
        "Specific requirement from the question that the response addressed"
    ],
    "missing_aspects": [
        "Specific requirement from the question that the response failed to address"
    ],
    "explanation": "Brief explanation of the completeness decision."
}}

Question:
{request.question}

AI-generated response:
{request.response}

Reference answer:
{request.reference_answer or "No reference answer provided."}
""".strip()

        result = await self.generate(prompt)

        addressed = result.get("addressed_aspects", [])
        missing = result.get("missing_aspects", [])

        # Ensure the values are always lists.
        if not isinstance(addressed, list):
            addressed = [str(addressed)]

        if not isinstance(missing, list):
            missing = [str(missing)]

        return {
            "score": float(result.get("score", 0.0)),
            "addressed_aspects": addressed,
            "missing_aspects": missing,
            "explanation": result.get("explanation", ""),
        }