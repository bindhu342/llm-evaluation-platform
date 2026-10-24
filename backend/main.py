from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from backend.api.evaluation_routes import router as evaluation_router
from backend.api.dashboard_routes import router as dashboard_router
from backend.database.database import init_db
import json
from collections import Counter
from statistics import mean
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import select

from backend.database.database import (
    BatchHistoryRecord,
    EvaluationRecord,
)
from backend.models.schemas import EvaluationResult
from backend.api.pdf_routes import router as pdf_router

router = APIRouter(
    prefix="/api/evaluation",
    tags=["Dashboard"],
)


# =========================================================
# HELPERS
# =========================================================

def safe_score(value) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0

    return max(
        0.0,
        min(1.0, value),
    )


def percentage(
    value: int,
    total: int,
) -> float:

    if total == 0:
        return 0.0

    return round(
        (value / total) * 100,
        2,
    )


def verdict_label(verdict: str) -> str:

    value = str(
        verdict or ""
    ).upper()

    if value == "PASS":
        return "PASS"

    if value == "NEEDS_IMPROVEMENT":
        return "NEEDS_IMPROVEMENT"

    if value == "FAIL":
        return "FAIL"

    return "UNKNOWN"


def score_bucket(
    score: float,
) -> str:

    score = safe_score(score)

    if score < 0.20:
        return "0.00-0.19"

    if score < 0.40:
        return "0.20-0.39"

    if score < 0.60:
        return "0.40-0.59"

    if score < 0.80:
        return "0.60-0.79"

    return "0.80-1.00"


def load_result(
    row: EvaluationRecord,
) -> EvaluationResult | None:

    if not row.result_json:
        return None

    try:
        return EvaluationResult.model_validate(
            json.loads(
                row.result_json
            )
        )

    except Exception:
        return None


# =========================================================
# DASHBOARD
# =========================================================

@router.get(
    "/dashboard",
)
async def get_dashboard(
    verdict: Optional[str] = Query(
        default=None
    ),
    min_score: Optional[float] = Query(
        default=None,
        ge=0.0,
        le=1.0,
    ),
    max_score: Optional[float] = Query(
        default=None,
        ge=0.0,
        le=1.0,
    ),
    batch_id: Optional[str] = Query(
        default=None
    ),
):

    # =====================================================
    # LOAD DATABASE
    # =====================================================

    from backend.database.database import (
        SessionLocal,
    )

    async with SessionLocal() as session:

        evaluation_query = (
            select(EvaluationRecord)
            .order_by(
                EvaluationRecord.created_at.asc()
            )
        )

        evaluation_result = (
            await session.execute(
                evaluation_query
            )
        )

        evaluation_rows = (
            evaluation_result
            .scalars()
            .all()
        )

        batch_query = (
            select(BatchHistoryRecord)
            .order_by(
                BatchHistoryRecord.created_at.asc()
            )
        )

        batch_result = (
            await session.execute(
                batch_query
            )
        )

        batch_rows = (
            batch_result
            .scalars()
            .all()
        )

    # =====================================================
    # LOAD STRUCTURED RESULTS
    # =====================================================

    evaluations = []

    for row in evaluation_rows:

        result = load_result(
            row
        )

        if result is None:
            continue

        evaluations.append(
            {
                "record": row,
                "result": result,
            }
        )

    # =====================================================
    # MAP EVALUATIONS TO BATCHES
    # =====================================================

    evaluation_batch_map: dict[
        str,
        str,
    ] = {}

    batch_summaries = []

    for batch in batch_rows:

        try:
            batch_data = json.loads(
                batch.batch_json
            )
        except Exception:
            batch_data = {}

        batch_items = (
            batch_data.get(
                "results",
                []
            )
        )

        batch_evaluation_ids = []

        for item in batch_items:

            evaluation_id = (
                item.get(
                    "evaluation_id"
                )
            )

            if evaluation_id:

                evaluation_batch_map[
                    evaluation_id
                ] = batch.batch_id

                batch_evaluation_ids.append(
                    evaluation_id
                )

        batch_summaries.append(
            {
                "batch_id": batch.batch_id,
                "filename": batch.filename
                or "Batch Evaluation",
                "created_at": batch.created_at,
                "total_rows": batch.total_rows,
                "completed_rows": batch.completed_rows,
                "failed_rows": batch.failed_rows,
                "invalid_rows": batch.invalid_rows,
                "average_final_score": safe_score(
                    batch.average_final_score
                ),
                "status": batch.status,
                "evaluation_count": len(
                    batch_evaluation_ids
                ),
            }
        )

    # =====================================================
    # FILTER
    # =====================================================

    filtered = []

    for item in evaluations:

        row = item["record"]
        result = item["result"]

        result_verdict = verdict_label(
            result.verdict
        )

        result_score = safe_score(
            result.final_score
        )

        result_batch_id = (
            evaluation_batch_map.get(
                result.id
            )
        )

        # -------------------------------------------------
        # Verdict filter
        # -------------------------------------------------

        if verdict:

            if (
                result_verdict
                != verdict_label(verdict)
            ):
                continue

        # -------------------------------------------------
        # Score filters
        # -------------------------------------------------

        if (
            min_score is not None
            and result_score < min_score
        ):
            continue

        if (
            max_score is not None
            and result_score > max_score
        ):
            continue

        # -------------------------------------------------
        # Batch filter
        # -------------------------------------------------

        if (
            batch_id
            and result_batch_id
            != batch_id
        ):
            continue

        filtered.append(
            {
                "record": row,
                "result": result,
                "batch_id": result_batch_id,
            }
        )

    # =====================================================
    # EMPTY DASHBOARD
    # =====================================================

    if not filtered:

        return {
            "filters": {
                "verdict": verdict,
                "min_score": min_score,
                "max_score": max_score,
                "batch_id": batch_id,
            },

            "overview": {
                "total_responses": 0,

                "pass_count": 0,
                "needs_improvement_count": 0,
                "fail_count": 0,

                "pass_percentage": 0.0,
                "needs_improvement_percentage": 0.0,
                "fail_percentage": 0.0,
            },

            "averages": {
                "relevance": 0.0,
                "accuracy": 0.0,
                "hallucination_free": 0.0,
                "completeness": 0.0,
                "final_score": 0.0,
            },

            "score_distribution": {
                "relevance": {},
                "accuracy": {},
                "hallucination_free": {},
                "completeness": {},
                "final_score": {},
            },

            "hallucination": {
                "responses_with_hallucinations": 0,
                "hallucination_frequency": 0.0,
                "unsupported_claims": 0,
                "contradicted_claims": 0,
                "partially_supported_cases": 0,
            },

            "completeness": {
                "responses_with_missing_information": 0,
                "missing_information_frequency": 0.0,
                "total_missing_aspects": 0,
                "most_common_missing_aspects": [],
            },

            "issues": [],

            "trends": [],

            "batches": batch_summaries,

            "evaluations": [],
        }

    # =====================================================
    # SCORE COLLECTION
    # =====================================================

    relevance_scores = []
    accuracy_scores = []
    hallucination_scores = []
    completeness_scores = []
    final_scores = []

    # =====================================================
    # VERDICT COUNTS
    # =====================================================

    pass_count = 0
    needs_improvement_count = 0
    fail_count = 0

    # =====================================================
    # HALLUCINATION
    # =====================================================

    hallucination_cases = 0
    unsupported_claims = 0
    contradicted_claims = 0
    partially_supported_cases = 0

    # =====================================================
    # COMPLETENESS
    # =====================================================

    missing_information_cases = 0
    total_missing_aspects = 0

    missing_aspect_counter = Counter()

    # =====================================================
    # ISSUE COUNTS
    # =====================================================

    issue_counter = Counter()

    # =====================================================
    # DISTRIBUTIONS
    # =====================================================

    distributions = {
        "relevance": Counter(),
        "accuracy": Counter(),
        "hallucination_free": Counter(),
        "completeness": Counter(),
        "final_score": Counter(),
    }

    # =====================================================
    # TREND DATA
    # =====================================================

    trend_map = {}

    # =====================================================
    # PROCESS EVALUATIONS
    # =====================================================

    for item in filtered:

        result = item["result"]

        relevance = safe_score(
            result.scores.relevance
        )

        accuracy = safe_score(
            result.scores.accuracy
        )

        hallucination_free = safe_score(
            result.scores.hallucination_free
        )

        completeness = safe_score(
            result.scores.completeness
        )

        final_score = safe_score(
            result.final_score
        )

        relevance_scores.append(
            relevance
        )

        accuracy_scores.append(
            accuracy
        )

        hallucination_scores.append(
            hallucination_free
        )

        completeness_scores.append(
            completeness
        )

        final_scores.append(
            final_score
        )

        # -------------------------------------------------
        # Verdict
        # -------------------------------------------------

        current_verdict = verdict_label(
            result.verdict
        )

        if current_verdict == "PASS":
            pass_count += 1

        elif current_verdict == "NEEDS_IMPROVEMENT":
            needs_improvement_count += 1

        elif current_verdict == "FAIL":
            fail_count += 1

        # -------------------------------------------------
        # Distribution
        # -------------------------------------------------

        distributions[
            "relevance"
        ][score_bucket(relevance)] += 1

        distributions[
            "accuracy"
        ][score_bucket(accuracy)] += 1

        distributions[
            "hallucination_free"
        ][score_bucket(hallucination_free)] += 1

        distributions[
            "completeness"
        ][score_bucket(completeness)] += 1

        distributions[
            "final_score"
        ][score_bucket(final_score)] += 1

        # -------------------------------------------------
        # Hallucination analysis
        # -------------------------------------------------

        hallucination_analysis = (
            result.hallucination_analysis
        )

        if hallucination_analysis:

            status = str(
                hallucination_analysis.status
                or "unknown"
            ).lower()

            claims = (
                hallucination_analysis.flagged_claims
                or []
            )

            if status in {
                "unsupported",
                "contradicted",
                "partially_supported",
            } or claims:

                hallucination_cases += 1

            if status == "unsupported":
                unsupported_claims += len(
                    claims
                )

            if status == "contradicted":
                contradicted_claims += len(
                    claims
                )

            if status == "partially_supported":
                partially_supported_cases += 1

            if claims:

                issue_counter[
                    "Hallucinated / unsupported claims"
                ] += 1

        # -------------------------------------------------
        # Completeness analysis
        # -------------------------------------------------

        completeness_analysis = (
            result.completeness_analysis
        )

        if completeness_analysis:

            missing = (
                completeness_analysis.missing_aspects
                or []
            )

            if missing:

                missing_information_cases += 1

                total_missing_aspects += len(
                    missing
                )

                issue_counter[
                    "Incomplete responses"
                ] += 1

                for aspect in missing:

                    cleaned = str(
                        aspect
                    ).strip()

                    if cleaned:

                        missing_aspect_counter[
                            cleaned
                        ] += 1

        # -------------------------------------------------
        # Other quality issues
        # -------------------------------------------------

        if relevance < 0.50:

            issue_counter[
                "Low relevance"
            ] += 1

        if accuracy < 0.50:

            issue_counter[
                "Low accuracy"
            ] += 1

        # -------------------------------------------------
        # Batch trend
        # -------------------------------------------------

        current_batch_id = (
            item["batch_id"]
        )

        if current_batch_id:

            if current_batch_id not in trend_map:

                trend_map[
                    current_batch_id
                ] = {
                    "scores": [],
                    "pass": 0,
                    "needs_improvement": 0,
                    "fail": 0,
                }

            trend = trend_map[
                current_batch_id
            ]

            trend["scores"].append(
                final_score
            )

            if current_verdict == "PASS":
                trend["pass"] += 1

            elif (
                current_verdict
                == "NEEDS_IMPROVEMENT"
            ):
                trend[
                    "needs_improvement"
                ] += 1

            elif current_verdict == "FAIL":
                trend["fail"] += 1

    # =====================================================
    # OVERALL TOTAL
    # =====================================================

    total = len(
        filtered
    )

    # =====================================================
    # BATCH TRENDS
    # =====================================================

    trends = []

    batch_lookup = {
        item["batch_id"]: item
        for item in batch_summaries
    }

    for current_batch_id, trend in trend_map.items():

        batch = batch_lookup.get(
            current_batch_id,
            {},
        )

        scores = trend["scores"]

        trends.append(
            {
                "batch_id": current_batch_id,

                "filename": batch.get(
                    "filename",
                    "Batch",
                ),

                "created_at": batch.get(
                    "created_at",
                    "",
                ),

                "average_final_score": round(
                    mean(scores),
                    4,
                )
                if scores
                else 0.0,

                "pass_count": trend["pass"],

                "needs_improvement_count": (
                    trend[
                        "needs_improvement"
                    ]
                ),

                "fail_count": trend["fail"],

                "total_evaluations": len(
                    scores
                ),
            }
        )

    trends.sort(
        key=lambda item: item[
            "created_at"
        ]
    )

    # =====================================================
    # MOST COMMON MISSING ASPECTS
    # =====================================================

    most_common_missing = [
        {
            "aspect": aspect,
            "count": count,
        }
        for aspect, count
        in missing_aspect_counter.most_common(
            10
        )
    ]

    # =====================================================
    # MOST FREQUENT ISSUES
    # =====================================================

    issues = [
        {
            "issue": issue,
            "count": count,
            "percentage": percentage(
                count,
                total,
            ),
        }
        for issue, count
        in issue_counter.most_common()
    ]

    # =====================================================
    # EVALUATION DRILL-DOWN DATA
    # =====================================================

    evaluation_items = []

    for item in filtered:

        result = item["result"]

        evaluation_items.append(
            {
                "id": result.id,

                "batch_id": item[
                    "batch_id"
                ],

                "created_at": (
                    item["record"].created_at
                    or ""
                ),

                "question": result.question,

                "final_score": safe_score(
                    result.final_score
                ),

                "verdict": verdict_label(
                    result.verdict
                ),

                "relevance": safe_score(
                    result.scores.relevance
                ),

                "accuracy": safe_score(
                    result.scores.accuracy
                ),

                "hallucination_free": safe_score(
                    result.scores.hallucination_free
                ),

                "completeness": safe_score(
                    result.scores.completeness
                ),
            }
        )

    # =====================================================
    # RETURN DASHBOARD
    # =====================================================

    return {

        "filters": {
            "verdict": verdict,
            "min_score": min_score,
            "max_score": max_score,
            "batch_id": batch_id,
        },

        "overview": {

            "total_responses": total,

            "pass_count": pass_count,

            "needs_improvement_count": (
                needs_improvement_count
            ),

            "fail_count": fail_count,

            "pass_percentage": percentage(
                pass_count,
                total,
            ),

            "needs_improvement_percentage": (
                percentage(
                    needs_improvement_count,
                    total,
                )
            ),

            "fail_percentage": percentage(
                fail_count,
                total,
            ),
        },

        "averages": {

            "relevance": round(
                mean(
                    relevance_scores
                ),
                4,
            ),

            "accuracy": round(
                mean(
                    accuracy_scores
                ),
                4,
            ),

            "hallucination_free": round(
                mean(
                    hallucination_scores
                ),
                4,
            ),

            "completeness": round(
                mean(
                    completeness_scores
                ),
                4,
            ),

            "final_score": round(
                mean(
                    final_scores
                ),
                4,
            ),
        },

        "score_distribution": {

            "relevance": dict(
                distributions[
                    "relevance"
                ]
            ),

            "accuracy": dict(
                distributions[
                    "accuracy"
                ]
            ),

            "hallucination_free": dict(
                distributions[
                    "hallucination_free"
                ]
            ),

            "completeness": dict(
                distributions[
                    "completeness"
                ]
            ),

            "final_score": dict(
                distributions[
                    "final_score"
                ]
            ),
        },

        "hallucination": {

            "responses_with_hallucinations": (
                hallucination_cases
            ),

            "hallucination_frequency": (
                percentage(
                    hallucination_cases,
                    total,
                )
            ),

            "unsupported_claims": (
                unsupported_claims
            ),

            "contradicted_claims": (
                contradicted_claims
            ),

            "partially_supported_cases": (
                partially_supported_cases
            ),
        },

        "completeness": {

            "responses_with_missing_information": (
                missing_information_cases
            ),

            "missing_information_frequency": (
                percentage(
                    missing_information_cases,
                    total,
                )
            ),

            "total_missing_aspects": (
                total_missing_aspects
            ),

            "most_common_missing_aspects": (
                most_common_missing
            ),
        },

        "issues": issues,

        "trends": trends,

        "batches": batch_summaries,

        "evaluations": evaluation_items,
    }


load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="LLM Evaluation Platform",
    description="Multi-agent AI response evaluation platform using LLM-as-a-Judge.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the Vite dev server and any configured frontend origin
_frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_frontend_origin, "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(evaluation_router)
app.include_router(dashboard_router)
app.include_router(pdf_router)

@app.get("/")
def root():
    return {"message": "LLM Evaluation Platform API is running", "status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
