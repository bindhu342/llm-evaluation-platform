from backend.models.schemas import AgentScores


WEIGHTS = {
    "relevance": 0.25,
    "accuracy": 0.30,
    "hallucination_free": 0.25,
    "completeness": 0.20,
}


def calculate_weighted_score(scores: AgentScores) -> float:
    """
    Calculate the final weighted evaluation score.

    All dimension scores are normalized to the range 0.0 - 1.0.
    """

    final_score = (
        scores.relevance * WEIGHTS["relevance"]
        + scores.accuracy * WEIGHTS["accuracy"]
        + scores.hallucination_free * WEIGHTS["hallucination_free"]
        + scores.completeness * WEIGHTS["completeness"]
    )

    return round(final_score, 4)


class VerdictAgent:
    """
    Combines the four evaluation dimensions into a weighted
    overall score and final verdict.
    """

    def evaluate(self, scores: AgentScores) -> tuple[float, str]:
        final_score = calculate_weighted_score(scores)

        # ---------------------------------------------------------
        # CRITICAL FAILURE RULES
        # ---------------------------------------------------------
        # Severe hallucination or factual failure should prevent
        # a passing verdict even if the weighted score is high.

        if (
            scores.hallucination_free < 0.50
            or scores.accuracy < 0.50
        ):
            verdict = "FAIL"

        # ---------------------------------------------------------
        # PASS
        # ---------------------------------------------------------

        elif final_score >= 0.70:
            verdict = "PASS"

        # ---------------------------------------------------------
        # NEEDS IMPROVEMENT
        # ---------------------------------------------------------

        elif final_score >= 0.50:
            verdict = "NEEDS_IMPROVEMENT"

        # ---------------------------------------------------------
        # FAIL
        # ---------------------------------------------------------

        else:
            verdict = "FAIL"

        return final_score, verdict