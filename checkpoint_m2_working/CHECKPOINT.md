# Checkpoint — M2 Working Baseline
**Date**: 2 September 2026  
**Status**: Live end-to-end test PASSED. All 4 Gemini agents executing. DB saving correctly.

---

## Backend Startup Command
```
cd c:\llm-evaluation-platform
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

---

## Environment Configuration (`.env`)
```
GEMINI_API_KEY=<AQ... key — do not change>
GEMINI_MODEL=gemini-3.5-flash-lite
DATABASE_URL=sqlite+aiosqlite:///./data/evaluations.db
VECTOR_STORE_PATH=./data/faiss_index
FRONTEND_ORIGIN=http://localhost:5173
```

---

## Gemini REST API Implementation
**File**: `backend/evaluation/base_agent.py`

- SDK: **none** — direct `httpx` REST call
- Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- Auth: API key passed as `?key=` query parameter (supports `AQ...` format)
- Model: `gemini-3.5-flash-lite` (set via `GEMINI_MODEL` env var)
- `maxOutputTokens`: 500
- `temperature`: 0
- Response parsing: extracts `candidates[0].content.parts[0].text`, strips markdown fences, parses JSON
- Return type: `{"score": float, "explanation": str}`
- Async: `asyncio.to_thread(_generate)` wraps the synchronous httpx call

---

## Database Schema
**File**: `backend/database/database.py`  
**Engine**: SQLite via SQLAlchemy async (`aiosqlite`)  
**Table**: `evaluations`

| Column | Type | Notes |
|---|---|---|
| id | String (PK) | UUID |
| question | Text | |
| response | Text | |
| scores | Text | JSON — `AgentScores` |
| explanations | Text | JSON — `AgentExplanations` |
| final_score | Float | |
| verdict | String | EXCELLENT / GOOD / FAIR / POOR |

---

## Evaluation Agents
All 4 agents inherit from `BaseAgent`. Each implements `async score(request) -> dict`.

| Agent | File | Input fields used |
|---|---|---|
| RelevanceAgent | `evaluation/relevance_agent.py` | `question`, `response` |
| AccuracyAgent | `evaluation/accuracy_agent.py` | `question`, `response`, `reference_answer` or `source_document` |
| HallucinationAgent | `evaluation/hallucination_agent.py` | `question`, `response`, `source_document` or `reference_answer` |
| CompletenessAgent | `evaluation/completeness_agent.py` | `question`, `response` |

---

## Parallel Execution
**File**: `backend/evaluation/orchestrator.py`

All 4 agents run concurrently via `asyncio.gather()`:
```python
rel, acc, hal, com = await asyncio.gather(
    self.relevance.score(request),
    self.accuracy.score(request),
    self.hallucination.score(request),
    self.completeness.score(request),
)
```

---

## Scoring Formula
**File**: `backend/evaluation/verdict_agent.py`

```
final_score = 0.25 × relevance
            + 0.30 × accuracy
            + 0.25 × hallucination_free
            + 0.20 × completeness
```

| Verdict | Threshold |
|---|---|
| EXCELLENT | ≥ 0.85 |
| GOOD | ≥ 0.70 |
| FAIR | ≥ 0.50 |
| POOR | < 0.50 |

---

## Schemas
**File**: `backend/models/schemas.py`

- `EvaluationRequest`: `question`, `response`, `reference_answer` (optional), `source_document` (optional)
- `AgentScores`: `relevance`, `accuracy`, `hallucination_free`, `completeness` (all float 0–1)
- `AgentExplanations`: same 4 fields as strings
- `EvaluationResult`: `id`, `question`, `response`, `scores`, `explanations`, `final_score`, `verdict`

---

## Live Test Result (Baseline)
```json
{
  "id": "1bbe05ec-4a48-4adb-9d1d-8b11096a40f4",
  "question": "What is the capital of France?",
  "response": "The capital of France is Paris.",
  "scores": {
    "relevance": 1.0,
    "accuracy": 1.0,
    "hallucination_free": 1.0,
    "completeness": 1.0
  },
  "explanations": {
    "relevance": "The response directly and accurately states that the capital of France is Paris.",
    "accuracy": "The response correctly identifies Paris as the capital of France, matching the reference completely.",
    "hallucination_free": "The response accurately and fully reflects the information provided in the reference.",
    "completeness": "The response accurately and completely answers the question about the capital of France."
  },
  "final_score": 1.0,
  "verdict": "EXCELLENT"
}
```

---

## Test Suite
**20/20 tests passing** — `python -m pytest tests/ -v`

- `tests/test_evaluation.py` — 10 tests (verdict logic + orchestrator integration)
- `tests/test_input.py` — 7 tests (schema validation)
- `tests/test_retrieval.py` — 3 tests (RAG retriever, mocked)
