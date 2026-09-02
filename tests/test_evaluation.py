import pytest
from unittest.mock import AsyncMock, patch
from backend.models.schemas import EvaluationRequest, AgentScores
from backend.evaluation.orchestrator import Orchestrator
from backend.evaluation.verdict_agent import VerdictAgent


# ── Helpers ──────────────────────────────────────────────────────

def _mock_score(score: float, explanation: str = "test explanation") -> dict:
    return {"score": score, "explanation": explanation}


# ── VerdictAgent unit tests ──────────────────────────────────────

def test_verdict_excellent():
    agent = VerdictAgent()
    scores = AgentScores(relevance=0.95, accuracy=0.95, hallucination_free=0.95, completeness=0.95)
    final, verdict = agent.evaluate(scores)
    assert verdict == "EXCELLENT"
    assert final >= 0.85


def test_verdict_good():
    agent = VerdictAgent()
    scores = AgentScores(relevance=0.75, accuracy=0.75, hallucination_free=0.75, completeness=0.75)
    final, verdict = agent.evaluate(scores)
    assert verdict == "GOOD"
    assert 0.70 <= final < 0.85


def test_verdict_fair():
    agent = VerdictAgent()
    scores = AgentScores(relevance=0.60, accuracy=0.55, hallucination_free=0.60, completeness=0.55)
    final, verdict = agent.evaluate(scores)
    assert verdict == "FAIR"
    assert 0.50 <= final < 0.70


def test_verdict_poor():
    agent = VerdictAgent()
    scores = AgentScores(relevance=0.2, accuracy=0.2, hallucination_free=0.1, completeness=0.2)
    final, verdict = agent.evaluate(scores)
    assert verdict == "POOR"
    assert final < 0.50


def test_verdict_formula_correct():
    agent = VerdictAgent()
    scores = AgentScores(relevance=1.0, accuracy=1.0, hallucination_free=1.0, completeness=1.0)
    final, verdict = agent.evaluate(scores)
    assert final == 1.0
    assert verdict == "EXCELLENT"


def test_hallucination_free_not_inverted():
    agent = VerdictAgent()
    scores_good = AgentScores(relevance=0.5, accuracy=0.5, hallucination_free=1.0, completeness=0.5)
    scores_bad  = AgentScores(relevance=0.5, accuracy=0.5, hallucination_free=0.0, completeness=0.5)
    final_good, _ = agent.evaluate(scores_good)
    final_bad,  _ = agent.evaluate(scores_bad)
    assert final_good > final_bad


# ── Orchestrator integration tests (mocked agents) ───────────────

@pytest.mark.asyncio
async def test_orchestrator_correct_answer():
    """Correct answer: Paris. Mocked agents return high scores."""
    request = EvaluationRequest(
        question="What is the capital of France?",
        response="The capital of France is Paris.",
        reference_answer="Paris is the capital of France.",
    )
    with patch("backend.evaluation.base_agent.BaseAgent.__init__", return_value=None):
        orchestrator = Orchestrator()

    with (
        patch.object(orchestrator.relevance,    "score", new=AsyncMock(return_value=_mock_score(0.95))),
        patch.object(orchestrator.accuracy,     "score", new=AsyncMock(return_value=_mock_score(0.95))),
        patch.object(orchestrator.hallucination,"score", new=AsyncMock(return_value=_mock_score(0.95))),
        patch.object(orchestrator.completeness, "score", new=AsyncMock(return_value=_mock_score(0.90))),
    ):
        result = await orchestrator.run(request)

    assert result.question == "What is the capital of France?"
    assert result.scores.relevance == 0.95
    assert result.scores.hallucination_free == 0.95
    assert result.final_score >= 0.85
    assert result.verdict == "EXCELLENT"
    assert result.explanations.relevance == "test explanation"


@pytest.mark.asyncio
async def test_orchestrator_incorrect_answer():
    """Incorrect answer: Berlin. Low accuracy and hallucination_free."""
    request = EvaluationRequest(
        question="What is the capital of France?",
        response="The capital of France is Berlin.",
        reference_answer="Paris is the capital of France.",
    )
    with patch("backend.evaluation.base_agent.BaseAgent.__init__", return_value=None):
        orchestrator = Orchestrator()

    with (
        patch.object(orchestrator.relevance,    "score", new=AsyncMock(return_value=_mock_score(0.80))),
        patch.object(orchestrator.accuracy,     "score", new=AsyncMock(return_value=_mock_score(0.10))),
        patch.object(orchestrator.hallucination,"score", new=AsyncMock(return_value=_mock_score(0.10))),
        patch.object(orchestrator.completeness, "score", new=AsyncMock(return_value=_mock_score(0.70))),
    ):
        result = await orchestrator.run(request)

    assert result.scores.accuracy < 0.50
    assert result.scores.hallucination_free < 0.50
    assert result.verdict in {"POOR", "FAIR"}


@pytest.mark.asyncio
async def test_orchestrator_incomplete_answer():
    """Incomplete answer: only one branch. Low completeness."""
    request = EvaluationRequest(
        question="What are the three branches of the US government and the primary role of each?",
        response="One branch is Congress, which makes laws.",
        reference_answer=(
            "Legislative (Congress — makes laws), "
            "Executive (President — enforces laws), "
            "Judicial (Supreme Court — interprets laws)."
        ),
    )
    with patch("backend.evaluation.base_agent.BaseAgent.__init__", return_value=None):
        orchestrator = Orchestrator()

    with (
        patch.object(orchestrator.relevance,    "score", new=AsyncMock(return_value=_mock_score(0.70))),
        patch.object(orchestrator.accuracy,     "score", new=AsyncMock(return_value=_mock_score(0.75))),
        patch.object(orchestrator.hallucination,"score", new=AsyncMock(return_value=_mock_score(0.90))),
        patch.object(orchestrator.completeness, "score", new=AsyncMock(return_value=_mock_score(0.25))),
    ):
        result = await orchestrator.run(request)

    assert result.scores.completeness < 0.50
    assert result.verdict in {"FAIR", "POOR", "GOOD"}


@pytest.mark.asyncio
async def test_orchestrator_result_fields():
    """Verify EvaluationResult contains all required fields including explanations."""
    request = EvaluationRequest(
        question="What is EC2?",
        response="EC2 provides virtual servers in the cloud.",
    )
    with patch("backend.evaluation.base_agent.BaseAgent.__init__", return_value=None):
        orchestrator = Orchestrator()

    with (
        patch.object(orchestrator.relevance,    "score", new=AsyncMock(return_value=_mock_score(0.9,  "Relevant"))),
        patch.object(orchestrator.accuracy,     "score", new=AsyncMock(return_value=_mock_score(0.85, "Accurate"))),
        patch.object(orchestrator.hallucination,"score", new=AsyncMock(return_value=_mock_score(0.9,  "Grounded"))),
        patch.object(orchestrator.completeness, "score", new=AsyncMock(return_value=_mock_score(0.8,  "Complete"))),
    ):
        result = await orchestrator.run(request)

    assert result.id is not None
    assert result.question == "What is EC2?"
    assert result.response == "EC2 provides virtual servers in the cloud."
    assert 0.0 <= result.final_score <= 1.0
    assert result.verdict in {"EXCELLENT", "GOOD", "FAIR", "POOR"}
    assert result.explanations.relevance == "Relevant"
    assert result.explanations.accuracy == "Accurate"
