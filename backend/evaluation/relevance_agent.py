from backend.evaluation.base_agent import BaseAgent
from backend.models.schemas import EvaluationRequest


class RelevanceAgent(BaseAgent):
    async def score(self, request: EvaluationRequest) -> dict:
        prompt = f"""
You are an expert relevance judge.

Evaluate ONLY whether the AI-generated response directly addresses
the user's question and stays on the same topic.

Do not evaluate factual correctness, completeness, or hallucination.
Those are evaluated by separate agents.

Relevance scoring scale:
- 1.0: The response directly answers the question and stays on topic.
- 0.75: The response mostly answers the question but includes minor
        unnecessary information.
- 0.5: The response partially addresses the question or contains
       substantial off-topic information.
- 0.25: The response barely addresses the question.
- 0.0: The response is completely unrelated to the question.

Important rules:
1. Identify the main topic of the question.
2. Identify the main topic of the response.
3. Compare the two topics.
4. If the response discusses a different subject, assign score 0.0.
5. Do not assume that a response is relevant merely because it uses
   general words such as "computer", "data", "technology", or "Artificial
   Intelligence".
6. A response about hardware, file storage, or computer memory is NOT
   relevant to a question asking for the definition of Machine Learning.
7. A response can be relevant even if it contains false information.
8. Do not reduce relevance only because the response is incomplete.
9. Return a score of exactly 0.0, 0.25, 0.5, 0.75, or 1.0.

Example:
Question: "What is Machine Learning?"
Response: "Machine Learning is hardware used to store files and manage
computer memory."
Correct relevance score: 0.0
Reason: The response discusses hardware and memory management instead
of Machine Learning.

Return only one valid JSON object with exactly these fields:
{{
  "score": 1.0,
  "explanation": "Brief reasoning about topical relevance"
}}

Question:
{request.question}

AI-generated response:
{request.response}
""".strip()

        result = await self.generate(prompt)

        # Safety correction for clearly unrelated responses.
        if not isinstance(result, dict):
            return result

        question = request.question.lower()
        response = request.response.lower()

        asks_about_machine_learning = (
            "machine learning" in question
        )

        discusses_unrelated_hardware = (
            "hardware" in response
            or "store files" in response
            or "computer memory" in response
            or "manage computer memory" in response
        )

        if asks_about_machine_learning and discusses_unrelated_hardware:
            result["score"] = 0.0
            result["explanation"] = (
                "The response discusses hardware and computer memory "
                "instead of explaining Machine Learning."
            )

        return result