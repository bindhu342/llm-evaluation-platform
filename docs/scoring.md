# Scoring Rubric

All agents return a score from **0.0 to 1.0**.

## Per-Agent Scoring

| Agent | Criteria | Weight |
|-------|----------|--------|
| Relevance | Does the response address the question? | 25% |
| Accuracy | Are the facts correct vs. context/ground truth? | 30% |
| Hallucination | Are there unsupported claims? (inverted) | 25% |
| Completeness | Are all parts of the question answered? | 20% |

## Final Verdict

```
final_score = (relevance * 0.25) + (accuracy * 0.30) +
              ((1 - hallucination) * 0.25) + (completeness * 0.20)
```

## Verdict Labels

| Score Range | Label |
|-------------|-------|
| 0.85 – 1.0 | EXCELLENT |
| 0.70 – 0.84 | GOOD |
| 0.50 – 0.69 | FAIR |
| 0.00 – 0.49 | POOR |
