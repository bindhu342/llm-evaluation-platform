from collections import Counter
from statistics import mean

from fastapi import APIRouter, Query

from backend.database.database import (
    get_history,
    get_result,
    get_batch_result,
)

from backend.models.schemas import (
    EvaluationResult,
)


router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
)


# =========================================================
# Helpers
# =========================================================

def _normalize_verdict(verdict: str | None) -> str:
    """
    Normalize all known historical and current verdict values
    into the standard dashboard categories.
    """

    if verdict is None:
        return "UNKNOWN"

    value = str(verdict).strip().upper()

    if not value:
        return "UNKNOWN"

    # -----------------------------------------------------
    # PASS
    # -----------------------------------------------------

    if value in {
        "PASS",
        "PASSED",
        "PASSING",
        "EXCELLENT",
        "GOOD",
        "SUCCESS",
    }:
        return "PASS"

    # -----------------------------------------------------
    # NEEDS IMPROVEMENT
    # -----------------------------------------------------

    if value in {
        "NEEDS_IMPROVEMENT",
        "NEEDS IMPROVEMENT",
        "NEEDS-IMPROVEMENT",
        "NEEDSIMPROVEMENT",
        "IMPROVEMENT",
        "AVERAGE",
        "FAIR",
    }:
        return "NEEDS_IMPROVEMENT"

    # -----------------------------------------------------
    # FAIL
    # -----------------------------------------------------

    if value in {
        "FAIL",
        "FAILED",
        "FAILING",
        "FAILURE",
        "POOR",
    }:
        return "FAIL"

    # -----------------------------------------------------
    # Unknown
    # -----------------------------------------------------

    return "UNKNOWN"


def _normalize_hallucination_status(
    status: str | None,
) -> str:

    if not status:
        return "unknown"

    return str(status).strip().lower()


def _score(value: float) -> float:
    return round(float(value), 4)


def _percentage(
    count: int,
    total: int,
) -> float:

    if total == 0:
        return 0.0

    return round(
        count / total * 100,
        2,
    )


def _score_band(score: float) -> str:

    if score < 0.25:
        return "0.00-0.24"

    if score < 0.50:
        return "0.25-0.49"

    if score < 0.75:
        return "0.50-0.74"

    return "0.75-1.00"


# =========================================================
# Empty Dashboard
# =========================================================

def _empty_dashboard():

    return {
        "total_responses": 0,

        "verdicts": {
            "pass": 0,
            "needs_improvement": 0,
            "fail": 0,
            "unknown": 0,
        },

        "verdict_percentages": {
            "pass": 0,
            "needs_improvement": 0,
            "fail": 0,
            "unknown": 0,
        },

        "raw_verdict_counts": {},

        "average_scores": {
            "relevance": 0,
            "accuracy": 0,
            "hallucination_free": 0,
            "completeness": 0,
            "final_score": 0,
        },

        "score_distribution": {
            "relevance": [],
            "accuracy": [],
            "hallucination_free": [],
            "completeness": [],
            "final_score": [],
        },

        "score_bands": {
            "relevance": {},
            "accuracy": {},
            "hallucination_free": {},
            "completeness": {},
            "final_score": {},
        },

        "hallucination": {
            "responses_with_hallucination": 0,
            "frequency": 0,
            "total_flagged_claims": 0,
            "average_flagged_claims_per_response": 0,
        },

        "completeness": {
            "responses_with_missing_information": 0,
            "frequency": 0,
            "total_missing_aspects": 0,
            "most_common_missing_aspects": [],
        },

        "issues": {
            "low_accuracy": 0,
            "low_relevance": 0,
            "incomplete_responses": 0,
            "hallucinations": 0,
        },

        "trends": [],

        "batches": [],

        "evaluations": [],

        "available_batches": [],

        "filters": {
            "verdict": None,
            "min_score": None,
            "max_score": None,
            "batch_id": None,
        },
    }


# =========================================================
# Dashboard Overview
# =========================================================

@router.get("/overview")
async def dashboard_overview(
    verdict: str | None = Query(
        default=None,
        description="Filter by verdict",
    ),
    min_score: float | None = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum final score",
    ),
    max_score: float | None = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description="Maximum final score",
    ),
    batch_id: str | None = Query(
        default=None,
        description="Filter by batch ID",
    ),
):

    # =====================================================
    # Load history
    # =====================================================

    history = await get_history()

    single_items = [
        item
        for item in history
        if item.get("type") == "single"
    ]

    batch_items = [
        item
        for item in history
        if item.get("type") == "batch"
    ]

    # =====================================================
    # Load individual evaluations
    # =====================================================

    evaluation_records = []

    # -----------------------------------------------------
    # Single evaluations
    # -----------------------------------------------------

    for item in single_items:

        result = await get_result(
            item["id"]
        )

        if not result:
            continue

        evaluation_records.append(
            {
                "id": result.id,
                "type": "single",
                "batch_id": None,
                "created_at": item.get(
                    "created_at",
                    "",
                ),
                "question": result.question,
                "response": result.response,
                "result": result,
            }
        )

    # -----------------------------------------------------
    # Batch evaluations
    # -----------------------------------------------------

    loaded_batches = []

    for item in batch_items:

        batch = await get_batch_result(
            item["id"]
        )

        if not batch:
            continue

        loaded_batches.append(batch)

        for batch_item in batch.results:

            if (
                batch_item.status == "completed"
                and batch_item.result
            ):

                evaluation_records.append(
                    {
                        "id": batch_item.result.id,

                        "type": "batch",

                        "batch_id": batch.batch_id,

                        "created_at": item.get(
                            "created_at",
                            "",
                        ),

                        "question": (
                            batch_item.result.question
                        ),

                        "response": (
                            batch_item.result.response
                        ),

                        "result": (
                            batch_item.result
                        ),
                    }
                )

    # =====================================================
    # Apply filters
    # =====================================================

    filtered_records = []

    normalized_filter_verdict = (
        _normalize_verdict(verdict)
        if verdict
        else None
    )

    for record in evaluation_records:

        result = record["result"]

        normalized_result_verdict = (
            _normalize_verdict(
                result.verdict
            )
        )

        # -------------------------------------------------
        # Verdict filter
        # -------------------------------------------------

        if (
            normalized_filter_verdict
            and normalized_result_verdict
            != normalized_filter_verdict
        ):
            continue

        # -------------------------------------------------
        # Batch filter
        # -------------------------------------------------

        if batch_id:

            if record["batch_id"] != batch_id:
                continue

        # -------------------------------------------------
        # Score filter
        # -------------------------------------------------

        if (
            min_score is not None
            and result.final_score < min_score
        ):
            continue

        if (
            max_score is not None
            and result.final_score > max_score
        ):
            continue

        filtered_records.append(record)

    # =====================================================
    # Empty result after filtering
    # =====================================================

    if not filtered_records:

        empty = _empty_dashboard()

        empty["filters"] = {
            "verdict": verdict,
            "min_score": min_score,
            "max_score": max_score,
            "batch_id": batch_id,
        }

        empty["available_batches"] = [
            {
                "batch_id": batch.batch_id,
                "filename": batch.filename,
            }
            for batch in loaded_batches
        ]

        return empty

    # =====================================================
    # Results
    # =====================================================

    results: list[EvaluationResult] = [
        record["result"]
        for record in filtered_records
    ]

    total = len(results)

    # =====================================================
    # Raw Verdict Statistics
    # =====================================================

    raw_verdict_counts = Counter()

    for result in results:

        if result.verdict is None:

            raw_verdict_counts["NULL"] += 1

        else:

            raw_value = str(
                result.verdict
            ).strip()

            if not raw_value:
                raw_verdict_counts["EMPTY"] += 1
            else:
                raw_verdict_counts[
                    raw_value
                ] += 1

    # =====================================================
    # Normalized Verdict Statistics
    # =====================================================

    normalized_verdicts = [
        _normalize_verdict(
            result.verdict
        )
        for result in results
    ]

    pass_count = normalized_verdicts.count(
        "PASS"
    )

    needs_count = normalized_verdicts.count(
        "NEEDS_IMPROVEMENT"
    )

    fail_count = normalized_verdicts.count(
        "FAIL"
    )

    unknown_count = normalized_verdicts.count(
        "UNKNOWN"
    )

    # =====================================================
    # Scores
    # =====================================================

    relevance = [
        result.scores.relevance
        for result in results
    ]

    accuracy = [
        result.scores.accuracy
        for result in results
    ]

    hallucination_free = [
        result.scores.hallucination_free
        for result in results
    ]

    completeness = [
        result.scores.completeness
        for result in results
    ]

    final_scores = [
        result.final_score
        for result in results
    ]

    # =====================================================
    # Hallucination Statistics
    # =====================================================

    hallucinated_results = []

    total_flagged_claims = 0

    for result in results:

        analysis = (
            result.hallucination_analysis
        )

        if not analysis:
            continue

        status = _normalize_hallucination_status(
            analysis.status
        )

        flagged_claims = (
            analysis.flagged_claims
            or []
        )

        flagged_claim_count = len(
            flagged_claims
        )

        total_flagged_claims += (
            flagged_claim_count
        )

        if (
            status not in {
                "supported",
                "unknown",
            }
            or flagged_claim_count > 0
        ):

            hallucinated_results.append(
                result
            )

    hallucination_count = len(
        hallucinated_results
    )

    # =====================================================
    # Completeness Statistics
    # =====================================================

    incomplete_results = []

    missing_aspects_counter = Counter()

    total_missing_aspects = 0

    for result in results:

        analysis = (
            result.completeness_analysis
        )

        if not analysis:
            continue

        missing = (
            analysis.missing_aspects
            or []
        )

        if missing:

            incomplete_results.append(
                result
            )

            total_missing_aspects += len(
                missing
            )

            for aspect in missing:

                cleaned = str(
                    aspect
                ).strip()

                if cleaned:

                    missing_aspects_counter[
                        cleaned
                    ] += 1

    incomplete_count = len(
        incomplete_results
    )

    most_common_missing_aspects = [
        {
            "aspect": aspect,
            "count": count,
            "frequency": _percentage(
                count,
                total,
            ),
        }
        for aspect, count
        in missing_aspects_counter.most_common(
            10
        )
    ]

    # =====================================================
    # Common Issues
    # =====================================================

    low_accuracy_count = sum(
        1
        for result in results
        if result.scores.accuracy < 0.50
    )

    low_relevance_count = sum(
        1
        for result in results
        if result.scores.relevance < 0.50
    )

    # =====================================================
    # Score Bands
    # =====================================================

    score_band_names = [
        "0.00-0.24",
        "0.25-0.49",
        "0.50-0.74",
        "0.75-1.00",
    ]

    def build_score_bands(
        values: list[float],
    ):

        counts = {
            band: 0
            for band in score_band_names
        }

        for value in values:

            band = _score_band(
                value
            )

            counts[band] += 1

        return counts

    # =====================================================
    # Batch Summaries
    # =====================================================

    batch_summaries = []

    for batch in loaded_batches:

        batch_results = [
            item.result
            for item in batch.results
            if (
                item.status == "completed"
                and item.result
            )
        ]

        if batch_results:

            batch_relevance = [
                r.scores.relevance
                for r in batch_results
            ]

            batch_accuracy = [
                r.scores.accuracy
                for r in batch_results
            ]

            batch_hallucination = [
                r.scores.hallucination_free
                for r in batch_results
            ]

            batch_completeness = [
                r.scores.completeness
                for r in batch_results
            ]

            batch_final = [
                r.final_score
                for r in batch_results
            ]

            batch_verdicts = [
                _normalize_verdict(
                    r.verdict
                )
                for r in batch_results
            ]

            batch_pass = batch_verdicts.count(
                "PASS"
            )

            batch_needs = batch_verdicts.count(
                "NEEDS_IMPROVEMENT"
            )

            batch_fail = batch_verdicts.count(
                "FAIL"
            )

            batch_hallucination_count = 0

            for r in batch_results:

                analysis = (
                    r.hallucination_analysis
                )

                if not analysis:
                    continue

                status = (
                    _normalize_hallucination_status(
                        analysis.status
                    )
                )

                flagged_claims = (
                    analysis.flagged_claims
                    or []
                )

                if (
                    status not in {
                        "supported",
                        "unknown",
                    }
                    or len(flagged_claims) > 0
                ):

                    batch_hallucination_count += 1

            batch_missing_count = sum(
                1
                for r in batch_results
                if (
                    r.completeness_analysis
                    and (
                        r.completeness_analysis
                        .missing_aspects
                        or []
                    )
                )
            )

            batch_summaries.append(
                {
                    "batch_id": batch.batch_id,

                    "filename": batch.filename,

                    "total_rows": (
                        batch.total_rows
                    ),

                    "completed_rows": (
                        batch.completed_rows
                    ),

                    "failed_rows": (
                        batch.failed_rows
                    ),

                    "invalid_rows": (
                        batch.invalid_rows
                    ),

                    "status": batch.status,

                    "average_relevance": _score(
                        mean(
                            batch_relevance
                        )
                    ),

                    "average_accuracy": _score(
                        mean(
                            batch_accuracy
                        )
                    ),

                    "average_hallucination_free": (
                        _score(
                            mean(
                                batch_hallucination
                            )
                        )
                    ),

                    "average_completeness": _score(
                        mean(
                            batch_completeness
                        )
                    ),

                    "average_final_score": _score(
                        mean(
                            batch_final
                        )
                    ),

                    "pass_count": batch_pass,

                    "needs_improvement_count": (
                        batch_needs
                    ),

                    "fail_count": batch_fail,

                    "unknown_count": batch_verdicts.count(
                        "UNKNOWN"
                    ),

                    "hallucination_count": (
                        batch_hallucination_count
                    ),

                    "incomplete_count": (
                        batch_missing_count
                    ),
                }
            )

        else:

            batch_summaries.append(
                {
                    "batch_id": batch.batch_id,

                    "filename": batch.filename,

                    "total_rows": (
                        batch.total_rows
                    ),

                    "completed_rows": (
                        batch.completed_rows
                    ),

                    "failed_rows": (
                        batch.failed_rows
                    ),

                    "invalid_rows": (
                        batch.invalid_rows
                    ),

                    "status": batch.status,

                    "average_relevance": 0,

                    "average_accuracy": 0,

                    "average_hallucination_free": 0,

                    "average_completeness": 0,

                    "average_final_score": 0,

                    "pass_count": 0,

                    "needs_improvement_count": 0,

                    "fail_count": 0,

                    "unknown_count": 0,

                    "hallucination_count": 0,

                    "incomplete_count": 0,
                }
            )

    # =====================================================
    # Trends
    # =====================================================

    trends = []

    for batch in loaded_batches:

        batch_results = [
            item.result
            for item in batch.results
            if (
                item.status == "completed"
                and item.result
            )
        ]

        if not batch_results:
            continue

        trend_verdicts = [
            _normalize_verdict(
                result.verdict
            )
            for result in batch_results
        ]

        trends.append(
            {
                "batch_id": batch.batch_id,

                "filename": batch.filename,

                "average_relevance": _score(
                    mean(
                        r.scores.relevance
                        for r in batch_results
                    )
                ),

                "average_accuracy": _score(
                    mean(
                        r.scores.accuracy
                        for r in batch_results
                    )
                ),

                "average_hallucination_free": _score(
                    mean(
                        r.scores.hallucination_free
                        for r in batch_results
                    )
                ),

                "average_completeness": _score(
                    mean(
                        r.scores.completeness
                        for r in batch_results
                    )
                ),

                "average_final_score": _score(
                    mean(
                        r.final_score
                        for r in batch_results
                    )
                ),

                "pass_count": trend_verdicts.count(
                    "PASS"
                ),

                "needs_improvement_count": (
                    trend_verdicts.count(
                        "NEEDS_IMPROVEMENT"
                    )
                ),

                "fail_count": trend_verdicts.count(
                    "FAIL"
                ),

                "unknown_count": trend_verdicts.count(
                    "UNKNOWN"
                ),
            }
        )

    # =====================================================
    # Individual Evaluation Records
    # =====================================================

    evaluation_summaries = []

    for record in filtered_records:

        result = record["result"]

        hallucination_analysis = (
            result.hallucination_analysis
        )

        completeness_analysis = (
            result.completeness_analysis
        )

        flagged_claims = (
            hallucination_analysis.flagged_claims
            if hallucination_analysis
            else []
        )

        missing_aspects = (
            completeness_analysis.missing_aspects
            if completeness_analysis
            else []
        )

        evaluation_summaries.append(
            {
                "id": result.id,

                "type": record["type"],

                "batch_id": record["batch_id"],

                "created_at": record[
                    "created_at"
                ],

                "question": result.question,

                "final_score": _score(
                    result.final_score
                ),

                "verdict": _normalize_verdict(
                    result.verdict
                ),

                "raw_verdict": (
                    result.verdict
                ),

                "relevance": _score(
                    result.scores.relevance
                ),

                "accuracy": _score(
                    result.scores.accuracy
                ),

                "hallucination_free": _score(
                    result.scores.hallucination_free
                ),

                "completeness": _score(
                    result.scores.completeness
                ),

                "has_hallucination": (
                    bool(
                        hallucination_analysis
                        and (
                            _normalize_hallucination_status(
                                hallucination_analysis.status
                            )
                            not in {
                                "supported",
                                "unknown",
                            }
                            or len(
                                flagged_claims
                            ) > 0
                        )
                    )
                ),

                "hallucinated_claim_count": (
                    len(flagged_claims)
                ),

                "missing_aspect_count": (
                    len(missing_aspects)
                ),

                "missing_aspects": (
                    missing_aspects
                ),
            }
        )

    # =====================================================
    # Response
    # =====================================================

    return {
        "total_responses": total,

        "verdicts": {
            "pass": pass_count,

            "needs_improvement": (
                needs_count
            ),

            "fail": fail_count,

            "unknown": unknown_count,
        },

        "verdict_percentages": {
            "pass": _percentage(
                pass_count,
                total,
            ),

            "needs_improvement": _percentage(
                needs_count,
                total,
            ),

            "fail": _percentage(
                fail_count,
                total,
            ),

            "unknown": _percentage(
                unknown_count,
                total,
            ),
        },

        "raw_verdict_counts": dict(
            raw_verdict_counts
        ),

        "average_scores": {
            "relevance": _score(
                mean(relevance)
            ),

            "accuracy": _score(
                mean(accuracy)
            ),

            "hallucination_free": _score(
                mean(hallucination_free)
            ),

            "completeness": _score(
                mean(completeness)
            ),

            "final_score": _score(
                mean(final_scores)
            ),
        },

        "score_distribution": {
            "relevance": relevance,

            "accuracy": accuracy,

            "hallucination_free": (
                hallucination_free
            ),

            "completeness": completeness,

            "final_score": final_scores,
        },

        "score_bands": {
            "relevance": build_score_bands(
                relevance
            ),

            "accuracy": build_score_bands(
                accuracy
            ),

            "hallucination_free": (
                build_score_bands(
                    hallucination_free
                )
            ),

            "completeness": build_score_bands(
                completeness
            ),

            "final_score": build_score_bands(
                final_scores
            ),
        },

        "hallucination": {
            "responses_with_hallucination": (
                hallucination_count
            ),

            "frequency": _percentage(
                hallucination_count,
                total,
            ),

            "total_flagged_claims": (
                total_flagged_claims
            ),

            "average_flagged_claims_per_response": (
                round(
                    total_flagged_claims / total,
                    4,
                )
            ),
        },

        "completeness": {
            "responses_with_missing_information": (
                incomplete_count
            ),

            "frequency": _percentage(
                incomplete_count,
                total,
            ),

            "total_missing_aspects": (
                total_missing_aspects
            ),

            "most_common_missing_aspects": (
                most_common_missing_aspects
            ),
        },

        "issues": {
            "low_accuracy": (
                low_accuracy_count
            ),

            "low_relevance": (
                low_relevance_count
            ),

            "incomplete_responses": (
                incomplete_count
            ),

            "hallucinations": (
                hallucination_count
            ),
        },

        "trends": trends,

        "batches": batch_summaries,

        "evaluations": evaluation_summaries,

        "available_batches": [
            {
                "batch_id": batch.batch_id,
                "filename": batch.filename,
            }
            for batch in loaded_batches
        ],

        "filters": {
            "verdict": verdict,
            "min_score": min_score,
            "max_score": max_score,
            "batch_id": batch_id,
        },
    }