from backend.models.schemas import AgentScores

# Configurable weights — must sum to 1.0
WEIGHTS = {
    "relevance": 0.25,
    "accuracy": 0.30,
    "hallucination_free": 0.25,
    "completeness": 0.20,
}

VERDICT_THRESHOLDS = [
    (0.85, "EXCELLENT"),
    (0.70, "GOOD"),
    (0.50, "FAIR"),
    (0.00, "POOR"),
]


class VerdictAgent:
    def evaluate(self, scores: AgentScores) -> tuple[float, str]:
        final = (
            scores.relevance * WEIGHTS["relevance"]
            + scores.accuracy * WEIGHTS["accuracy"]
            + scores.hallucination_free * WEIGHTS["hallucination_free"]
            + scores.completeness * WEIGHTS["completeness"]
        )
        final = round(final, 4)

        verdict = "POOR"
        for threshold, label in VERDICT_THRESHOLDS:
            if final >= threshold:
                verdict = label
                break

        return final, verdict
