from backend.evaluation.base_agent import BaseAgent
from backend.models.schemas import EvaluationRequest
from backend.rag.retriever import retrieve


class HallucinationAgent(BaseAgent):
    async def score(self, request: EvaluationRequest) -> dict:
        """
        Detect unsupported, fabricated, contradictory, or irrelevant
        factual claims in the AI-generated response.
        """

        reference = request.source_document or request.reference_answer

        if reference:
            evidence = reference
            evidence_instruction = (
                "Use the provided source document or reference answer "
                "as the primary evidence."
            )
        else:
            retrieved_chunks = retrieve(request.question, k=4)

            if retrieved_chunks:
                evidence = "\n\n".join(retrieved_chunks)
                evidence_instruction = (
                    "Use the retrieved knowledge-base chunks as the "
                    "primary evidence for checking factual claims."
                )
            else:
                evidence = (
                    "No source document, reference answer, or retrieved "
                    "knowledge-base evidence is available."
                )
                evidence_instruction = (
                    "No reliable evidence is available. Treat claims "
                    "that cannot be verified as unsupported."
                )

        prompt = f"""
You are an expert hallucination-detection judge.

{evidence_instruction}

Break the AI-generated response into individual factual claims.
Cross-reference every claim against the available evidence.

Identify claims that are:
- unsupported
- fabricated
- contradictory
- not verifiable from the available evidence
- unrelated to the question

Do not flag opinions, clearly marked assumptions, or harmless wording
as hallucinations unless they contain an unsupported factual claim.

Hallucination-free scoring scale:
1.0 = every factual claim is supported
0.75 = mostly supported with minor uncertainty
0.5 = some claims are unsupported or questionable
0.25 = many claims are unsupported or fabricated
0.0 = heavily fabricated, contradictory, or unrelated response

Status must be exactly one of:
- supported
- partially_supported
- unsupported
- contradicted

Consistency requirements:
1. The status, score, explanation, and flagged_claims must agree.
2. Never return status "supported" if any claim is unsupported,
   fabricated, unverifiable, unrelated, or contradictory.
3. If a claim directly conflicts with the evidence, use "contradicted".
4. If some claims are supported and others are unsupported, use
   "partially_supported".
5. If the response is unrelated to the question, use "unsupported".
6. Every unsupported or contradictory claim must be included in
   flagged_claims.
7. If status is "supported", flagged_claims must be an empty list.
8. Do not flag a correct claim merely because the explanation contains
   words such as "unsupported" or "contradictory" while describing
   the absence of hallucinations.
9. Before returning JSON, verify that all fields are internally
   consistent.

Return only one valid JSON object with exactly these fields:
{{
  "score": 1.0,
  "status": "supported",
  "explanation": "Brief overall reasoning",
  "flagged_claims": [
    {{
      "claim": "Exact unsupported or contradictory claim",
      "reason": "Why the claim is unsupported or contradictory",
      "evidence": "Relevant supporting or contradicting evidence"
    }}
  ]
}}

If no unsupported claims are found, return an empty flagged_claims array.

Evidence:
{evidence}

Question:
{request.question}

AI-generated response:
{request.response}
""".strip()

        result = await self.generate(prompt)

        if not isinstance(result, dict):
            return result

        # Normalize flagged claims.
        flagged_claims = result.get("flagged_claims") or []

        if not isinstance(flagged_claims, list):
            flagged_claims = []

        # Normalize score.
        try:
            score = float(result.get("score", 1.0))
        except (TypeError, ValueError):
            score = 1.0

        score = max(0.0, min(1.0, score))

        # Read and normalize the model's status.
        valid_statuses = {
            "supported",
            "partially_supported",
            "unsupported",
            "contradicted",
        }

        model_status = str(result.get("status", "")).strip().lower()

        # A non-empty flagged_claims list takes priority over a
        # contradictory model status of "supported".
        if flagged_claims:
            if model_status in {"contradicted", "unsupported"}:
                status = model_status
            else:
                status = "partially_supported"

        elif model_status in valid_statuses:
            status = model_status

        elif score <= 0.25:
            status = "unsupported"

        else:
            status = "supported"

        # A supported response must not contain flagged claims.
        if status == "supported":
            flagged_claims = []
            score = 1.0

        # If a problematic status has no flagged claims, create a
        # fallback claim to preserve explainability.
        elif not flagged_claims:
            flagged_claims = [
                {
                    "claim": request.response,
                    "reason": (
                        "The response contains unsupported, fabricated, "
                        "unverifiable, irrelevant, or contradictory content."
                    ),
                    "evidence": evidence,
                }
            ]

        # Align the score with the final status.
        if status in {"unsupported", "contradicted"}:
            score = min(score, 0.25)

        elif status == "partially_supported":
            score = min(max(score, 0.5), 0.75)

        result["score"] = score
        result["status"] = status
        result["flagged_claims"] = flagged_claims

        return result