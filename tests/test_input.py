import pytest
from pydantic import ValidationError
from backend.models.schemas import EvaluationRequest


# ── Schema validation tests ──────────────────────────────────────

def test_valid_request_minimal():
    req = EvaluationRequest(
        question="What is AWS?",
        response="AWS is Amazon Web Services.",
    )
    assert req.question == "What is AWS?"
    assert req.reference_answer is None
    assert req.source_document is None


def test_valid_request_with_reference():
    req = EvaluationRequest(
        question="What is S3?",
        response="S3 is object storage.",
        reference_answer="Amazon S3 provides scalable object storage.",
        source_document="Amazon S3 is a service offered by AWS.",
    )
    assert req.reference_answer is not None
    assert req.source_document is not None


def test_empty_question_rejected():
    with pytest.raises(ValidationError):
        EvaluationRequest(question="", response="some response")


def test_empty_response_rejected():
    with pytest.raises(ValidationError):
        EvaluationRequest(question="What is AWS?", response="")


# ── Correct answer scenario ──────────────────────────────────────

def test_correct_answer_request_is_valid():
    """
    Correct answer: Paris is the capital of France.
    Expected: high relevance, accuracy, hallucination_free, completeness.
    (Actual scoring requires Bedrock — this test validates the request is well-formed.)
    """
    req = EvaluationRequest(
        question="What is the capital of France?",
        response="The capital of France is Paris.",
        reference_answer="Paris is the capital of France.",
    )
    assert req.question == "What is the capital of France?"
    assert req.reference_answer == "Paris is the capital of France."


# ── Incorrect answer scenario ────────────────────────────────────

def test_incorrect_answer_request_is_valid():
    """
    Incorrect answer: Berlin instead of Paris.
    Expected: low accuracy, low hallucination_free.
    (Actual scoring requires Bedrock — this test validates the request is well-formed.)
    """
    req = EvaluationRequest(
        question="What is the capital of France?",
        response="The capital of France is Berlin.",
        reference_answer="Paris is the capital of France.",
    )
    assert req.response == "The capital of France is Berlin."


# ── Incomplete answer scenario ───────────────────────────────────

def test_incomplete_answer_request_is_valid():
    """
    Incomplete answer: only partially answers a multi-part question.
    Expected: lower completeness score.
    (Actual scoring requires Bedrock — this test validates the request is well-formed.)
    """
    req = EvaluationRequest(
        question=(
            "What are the three branches of the US government "
            "and what is the primary role of each?"
        ),
        response="One branch is Congress, which makes laws.",
        reference_answer=(
            "The three branches are: Legislative (Congress — makes laws), "
            "Executive (President — enforces laws), "
            "Judicial (Supreme Court — interprets laws)."
        ),
    )
    assert req.question is not None
    assert req.response is not None
