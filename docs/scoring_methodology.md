# Scoring Methodology

**Project:** Robust LLM Response Evaluation Platform  
**Milestone:** M1 — Proposed Scoring Design  
**Date:** August 2025

---

## Overview

The platform evaluates LLM responses across four independent quality dimensions. Each dimension is scored by a dedicated evaluation agent using an LLM-as-a-Judge approach. All scores are normalised to the range **0.0 to 1.0**. A weighted formula combines the four scores into a single final score, which is then mapped to a verdict label.

---

## Evaluation Dimensions

### 1. Relevance

Measures how well the response addresses the specific question or prompt that was asked.

| Score | Meaning |
|---|---|
| 1.0 | Response directly and fully addresses the question |
| 0.5 | Response partially addresses the question or drifts off-topic |
| 0.0 | Response is completely irrelevant to the question |

### 2. Accuracy

Measures the factual correctness of the response against the retrieved reference context or ground truth answer.

| Score | Meaning |
|---|---|
| 1.0 | All facts in the response are correct |
| 0.5 | Some facts are correct, some are incorrect |
| 0.0 | The response is factually wrong |

### 3. Hallucination-Free Score

Measures the absence of unsupported or fabricated claims. The Hallucination Agent produces a raw hallucination score (0 = none, 1 = fully hallucinated). This is **inverted** in the final formula so that a hallucination-free response contributes positively.

| Raw Hallucination Score | Hallucination-Free Score | Meaning |
|---|---|---|
| 0.0 | 1.0 | No hallucination detected |
| 0.5 | 0.5 | Some unsupported claims present |
| 1.0 | 0.0 | Response is entirely hallucinated |

### 4. Completeness

Measures whether the response covers all aspects of the question.

| Score | Meaning |
|---|---|
| 1.0 | Response fully addresses all parts of the question |
| 0.5 | Response addresses some but not all parts |
| 0.0 | Response is incomplete or only superficially answers the question |

---

## Final Score Formula

```
Final Score =
    0.25 × Relevance
  + 0.30 × Accuracy
  + 0.25 × (1 − Hallucination)
  + 0.20 × Completeness
```

The weights sum to **1.0**. The final score is in the range **[0.0, 1.0]**.

### Weight Rationale

| Dimension | Weight | Rationale |
|---|---|---|
| Relevance | 0.25 | A response must address the question, but relevance alone is insufficient |
| Accuracy | 0.30 | Factual correctness is the most critical dimension for a trustworthy response |
| Hallucination-Free | 0.25 | Unsupported claims are a serious failure mode that undermines trust |
| Completeness | 0.20 | Partial answers are acceptable in some contexts; weighted slightly lower |

> The weights are configurable and may be refined in later milestones based on empirical evaluation against benchmark datasets (TruthfulQA, SQuAD).

---

## Verdict Labels

The final score is mapped to a human-readable verdict:

| Score Range | Verdict | Meaning |
|---|---|---|
| 0.85 – 1.00 | **EXCELLENT** | High-quality response across all dimensions |
| 0.70 – 0.84 | **GOOD** | Generally reliable response with minor issues |
| 0.50 – 0.69 | **FAIR** | Acceptable but with notable quality issues |
| 0.00 – 0.49 | **POOR** | Unreliable response — significant quality problems |

---

## Worked Example

Given the following agent scores for a response:

| Dimension | Score |
|---|---|
| Relevance | 0.90 |
| Accuracy | 0.85 |
| Hallucination (raw) | 0.10 |
| Completeness | 0.80 |

```
Final Score = (0.25 × 0.90) + (0.30 × 0.85) + (0.25 × 0.90) + (0.20 × 0.80)
            =  0.225        +  0.255        +  0.225        +  0.160
            =  0.865

Verdict: EXCELLENT
```

---

## Future Refinements

The following refinements are planned for later milestones:

- **Configurable weights** — allow users to adjust dimension weights based on their use case
- **Empirical calibration** — refine weights based on correlation with human judgements on TruthfulQA and SQuAD benchmarks
- **RAGAS integration** — complement custom agent scores with standardised RAGAS metrics (faithfulness, answer relevancy, context precision)
- **Confidence intervals** — run each agent multiple times and report score variance
