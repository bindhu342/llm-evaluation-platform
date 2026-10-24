# backend/evaluation/accuracy_agent.py

from backend.evaluation.base_agent import BaseAgent
from backend.models.schemas import EvaluationRequest
from backend.rag.retriever import retrieve


class AccuracyAgent(BaseAgent):
    async def score(self, request: EvaluationRequest) -> dict:
        """
        Evaluate factual accuracy using reference information or RAG evidence.
        """

        reference = request.reference_answer or request.source_document

        if reference:
            evidence = reference
            evidence_instruction = (
                "Compare the AI-generated response directly against the "
                "provided reference information."
            )
        else:
            retrieved_chunks = retrieve(request.question, k=4)

            if retrieved_chunks:
                evidence = "\n\n".join(retrieved_chunks)
                evidence_instruction = (
                    "Use the retrieved knowledge-base chunks as the primary "
                    "evidence for judging factual accuracy."
                )
            else:
                evidence = (
                    "No reference answer, source document, or retrieved "
                    "knowledge-base evidence is available."
                )
                evidence_instruction = (
                    "Evidence is unavailable. Do not assume unsupported claims "
                    "are correct. Mention this limitation in the explanation."
                )

        prompt = f"""
You are an expert factual-accuracy judge.

{evidence_instruction}

Evaluate only factual correctness. Do not judge relevance, completeness,
writing style, or hallucination separately.

Scoring scale:
1.0 = all important claims are correct and supported
0.75 = mostly correct with minor omissions or imprecision
0.5 = partially correct; some claims are missing or questionable
0.25 = mostly incorrect or substantially unsupported
0.0 = clearly false or contradictory

Classification must be exactly one of:
- correct
- partially_correct
- incorrect
- unsupported

Return only one valid JSON object with exactly these fields:
{{
  "score": 0.0,
  "classification": "correct",
  "explanation": "Brief factual reasoning",
  "supporting_evidence": ["Relevant evidence"]
}}

Evidence:
{evidence}

Question:
{request.question}

AI-generated response:
{request.response}
""".strip()

        return await self.generate(prompt)