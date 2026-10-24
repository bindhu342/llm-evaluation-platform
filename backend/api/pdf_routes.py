from io import BytesIO
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)

from backend.database.database import (
    get_result,
    get_batch_result,
)


router = APIRouter(
    prefix="/api/evaluation",
    tags=["PDF Reports"],
)


# =========================================================
# HELPERS
# =========================================================

def safe_value(
    value: Any,
    default: str = "Not available",
) -> str:
    if value is None:
        return default

    if isinstance(value, str):
        return value.strip() or default

    return str(value)


def score_value(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0

    if number > 1:
        number = number / 100

    return max(0.0, min(1.0, number))


def score_percent(value: Any) -> str:
    return f"{score_value(value) * 100:.1f}%"


def get_field(
    obj: Any,
    name: str,
    default=None,
):
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(name, default)

    return getattr(obj, name, default)


def get_nested(
    obj: Any,
    *names: str,
    default=None,
):
    current = obj

    for name in names:
        current = get_field(
            current,
            name,
            None,
        )

        if current is None:
            return default

    return current


def format_list(items: Any) -> list[str]:
    if items is None:
        return []

    if isinstance(items, (list, tuple)):
        result = []

        for item in items:
            if isinstance(item, dict):
                text = (
                    item.get("aspect")
                    or item.get("claim")
                    or item.get("text")
                    or item.get("reason")
                    or str(item)
                )
            else:
                text = str(item)

            if text.strip():
                result.append(text.strip())

        return result

    if isinstance(items, str):
        return (
            [items.strip()]
            if items.strip()
            else []
        )

    return [str(items)]


def to_dict(value: Any) -> dict:
    """
    Convert Pydantic models or dictionaries
    into a normal dictionary.
    """
    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    if hasattr(value, "model_dump"):
        try:
            return value.model_dump()
        except Exception:
            pass

    if hasattr(value, "dict"):
        try:
            return value.dict()
        except Exception:
            pass

    return {}


def find_batch_items(batch: Any) -> list[Any]:
    """
    Find evaluation records inside a BatchEvaluationResult.

    Different schema versions may use different field names,
    so this checks the common possibilities.
    """

    possible_names = [
        "evaluations",
        "results",
        "items",
        "responses",
        "evaluation_results",
        "records",
        "details",
        "rows",
    ]

    for name in possible_names:
        value = get_field(
            batch,
            name,
            None,
        )

        if isinstance(value, (list, tuple)):
            return list(value)

    return []


def get_batch_statistics(
    batch: Any,
    items: list[Any],
) -> dict:
    """
    Calculate statistics from the batch itself.

    Falls back to the stored batch statistics when available.
    """

    statistics = get_field(
        batch,
        "statistics",
        None,
    )

    statistics_dict = to_dict(
        statistics
    )

    total = get_field(
        batch,
        "total_rows",
        len(items),
    )

    completed = get_field(
        batch,
        "completed_rows",
        len(items),
    )

    failed = get_field(
        batch,
        "failed_rows",
        0,
    )

    invalid = get_field(
        batch,
        "invalid_rows",
        0,
    )

    # -----------------------------------------------------
    # Scores
    # -----------------------------------------------------

    score_values = {
        "relevance": [],
        "accuracy": [],
        "hallucination_free": [],
        "completeness": [],
        "final_score": [],
    }

    verdict_counts = {
        "PASS": 0,
        "NEEDS_IMPROVEMENT": 0,
        "FAIL": 0,
        "UNKNOWN": 0,
    }

    hallucination_count = 0

    for item in items:

        scores = get_field(
            item,
            "scores",
            None,
        )

        score_values["relevance"].append(
            score_value(
                get_field(
                    scores,
                    "relevance",
                    0,
                )
            )
        )

        score_values["accuracy"].append(
            score_value(
                get_field(
                    scores,
                    "accuracy",
                    0,
                )
            )
        )

        score_values["hallucination_free"].append(
            score_value(
                get_field(
                    scores,
                    "hallucination_free",
                    0,
                )
            )
        )

        score_values["completeness"].append(
            score_value(
                get_field(
                    scores,
                    "completeness",
                    0,
                )
            )
        )

        score_values["final_score"].append(
            score_value(
                get_field(
                    item,
                    "final_score",
                    0,
                )
            )
        )

        verdict = safe_value(
            get_field(
                item,
                "verdict",
                None,
            ),
            "UNKNOWN",
        ).strip().upper()

        if verdict in {
            "PASSED",
            "PASSING",
            "EXCELLENT",
            "GOOD",
        }:
            verdict = "PASS"

        elif verdict in {
            "NEEDS IMPROVEMENT",
            "NEEDS-IMPROVEMENT",
            "NEEDSIMPROVEMENT",
            "IMPROVEMENT",
            "FAIR",
        }:
            verdict = "NEEDS_IMPROVEMENT"

        elif verdict in {
            "FAILED",
            "FAILING",
            "FAILURE",
            "POOR",
        }:
            verdict = "FAIL"

        elif verdict not in {
            "PASS",
            "NEEDS_IMPROVEMENT",
            "FAIL",
        }:
            verdict = "UNKNOWN"

        verdict_counts[verdict] += 1

        hallucination = get_field(
            item,
            "hallucination_analysis",
            None,
        )

        hallucination_status = safe_value(
            get_field(
                hallucination,
                "status",
                "",
            ),
            "",
        ).lower()

        flagged_claims = get_field(
            hallucination,
            "flagged_claims",
            [],
        ) or []

        if (
            flagged_claims
            or hallucination_status
            in {
                "hallucination",
                "detected",
                "flagged",
                "present",
                "true",
            }
        ):
            hallucination_count += 1

    # -----------------------------------------------------
    # Average helper
    # -----------------------------------------------------

    def average(values):
        if not values:
            return 0.0

        return sum(values) / len(values)

    calculated = {
        key: average(value)
        for key, value in score_values.items()
    }

    # Use stored final score when available.
    stored_final = statistics_dict.get(
        "average_final_score"
    )

    if stored_final is not None:
        calculated["final_score"] = score_value(
            stored_final
        )

    return {
        "total": int(total or 0),
        "completed": int(completed or 0),
        "failed": int(failed or 0),
        "invalid": int(invalid or 0),
        "relevance": calculated["relevance"],
        "accuracy": calculated["accuracy"],
        "hallucination_free": calculated[
            "hallucination_free"
        ],
        "completeness": calculated[
            "completeness"
        ],
        "final_score": calculated["final_score"],
        "verdict_counts": verdict_counts,
        "hallucination_count": hallucination_count,
    }


def extract_explanation(
    result: Any,
    dimension: str,
) -> str:

    explanations = get_field(
        result,
        "explanations",
        {},
    ) or {}

    if isinstance(explanations, dict):

        explanation = explanations.get(
            dimension
        )

        if explanation:
            return safe_value(
                explanation
            )

    analysis = get_field(
        result,
        f"{dimension}_analysis",
        None,
    )

    if analysis is not None:

        explanation = get_field(
            analysis,
            "explanation",
            None,
        )

        if explanation:
            return safe_value(
                explanation
            )

    return "No explanation available."


# =========================================================
# PDF STYLES
# =========================================================

PAGE_WIDTH, PAGE_HEIGHT = A4

styles = getSampleStyleSheet()


TITLE_STYLE = ParagraphStyle(
    "ReportTitle",
    parent=styles["Title"],
    fontName="Helvetica-Bold",
    fontSize=22,
    leading=27,
    alignment=TA_CENTER,
    spaceAfter=8,
)


SUBTITLE_STYLE = ParagraphStyle(
    "ReportSubtitle",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=9,
    leading=13,
    alignment=TA_CENTER,
    textColor=colors.HexColor("#64748b"),
    spaceAfter=18,
)


SECTION_STYLE = ParagraphStyle(
    "Section",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=14,
    leading=18,
    textColor=colors.HexColor("#0f172a"),
    spaceBefore=10,
    spaceAfter=8,
)


BODY_STYLE = ParagraphStyle(
    "Body",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=9,
    leading=14,
    textColor=colors.HexColor("#334155"),
    spaceAfter=6,
)


SMALL_STYLE = ParagraphStyle(
    "Small",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=7.5,
    leading=10,
    textColor=colors.HexColor("#475569"),
)


SCORE_STYLE = ParagraphStyle(
    "Score",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=16,
    leading=20,
    alignment=TA_CENTER,
    textColor=colors.HexColor("#0f172a"),
)


CENTER_STYLE = ParagraphStyle(
    "Center",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=9,
    leading=13,
    alignment=TA_CENTER,
    textColor=colors.HexColor("#334155"),
)


WHITE_BOLD_STYLE = ParagraphStyle(
    "WhiteBold",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=10,
    leading=13,
    textColor=colors.white,
)


# =========================================================
# PAGE HEADER / FOOTER
# =========================================================

def draw_page(
    canvas,
    document,
):
    canvas.saveState()

    canvas.setStrokeColor(
        colors.HexColor("#e2e8f0")
    )

    canvas.setLineWidth(0.6)

    canvas.line(
        18 * mm,
        PAGE_HEIGHT - 15 * mm,
        PAGE_WIDTH - 18 * mm,
        PAGE_HEIGHT - 15 * mm,
    )

    canvas.setFont(
        "Helvetica",
        7,
    )

    canvas.setFillColor(
        colors.HexColor("#64748b")
    )

    canvas.drawString(
        18 * mm,
        PAGE_HEIGHT - 11 * mm,
        "VALID — AI Response Evaluation Platform",
    )

    canvas.line(
        18 * mm,
        14 * mm,
        PAGE_WIDTH - 18 * mm,
        14 * mm,
    )

    canvas.drawString(
        18 * mm,
        9 * mm,
        "Generated by VALID",
    )

    canvas.drawRightString(
        PAGE_WIDTH - 18 * mm,
        9 * mm,
        f"Page {document.page}",
    )

    canvas.restoreState()


# =========================================================
# COMMON DOCUMENT
# =========================================================

def create_document(
    buffer: BytesIO,
    title: str,
):
    return SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        title=title,
        author="VALID",
    )


# =========================================================
# SINGLE EVALUATION PDF
# =========================================================

def build_evaluation_pdf(
    result: Any,
) -> BytesIO:

    buffer = BytesIO()

    evaluation_id = safe_value(
        get_field(result, "id"),
        "Unknown",
    )

    question = safe_value(
        get_field(result, "question"),
    )

    response = safe_value(
        get_field(result, "response"),
    )

    reference_answer = safe_value(
        get_field(result, "reference_answer"),
        "No reference answer provided.",
    )

    final_score = score_value(
        get_field(
            result,
            "final_score",
            0,
        )
    )

    verdict = safe_value(
        get_field(
            result,
            "verdict",
        ),
        "UNKNOWN",
    ).upper()

    scores = get_field(
        result,
        "scores",
        {},
    ) or {}

    relevance = score_value(
        get_field(
            scores,
            "relevance",
            0,
        )
    )

    accuracy = score_value(
        get_field(
            scores,
            "accuracy",
            0,
        )
    )

    hallucination_free = score_value(
        get_field(
            scores,
            "hallucination_free",
            0,
        )
    )

    completeness = score_value(
        get_field(
            scores,
            "completeness",
            0,
        )
    )

    hallucination = get_field(
        result,
        "hallucination_analysis",
        None,
    )

    completeness_analysis = get_field(
        result,
        "completeness_analysis",
        None,
    )

    recommendation = get_field(
        result,
        "recommendation",
        None,
    )

    consolidated_explanation = get_field(
        result,
        "explanation",
        None,
    )

    document = create_document(
        buffer,
        "VALID Evaluation Report",
    )

    story = []

    story.append(
        Paragraph(
            "VALID Evaluation Report",
            TITLE_STYLE,
        )
    )

    story.append(
        Paragraph(
            "AI Response Quality & Reliability Analysis",
            SUBTITLE_STYLE,
        )
    )

    metadata = Table(
        [
            [
                Paragraph(
                    "<b>Evaluation ID</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    evaluation_id,
                    BODY_STYLE,
                ),
            ],
            [
                Paragraph(
                    "<b>Verdict</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    verdict,
                    BODY_STYLE,
                ),
            ],
            [
                Paragraph(
                    "<b>Final Score</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    score_percent(final_score),
                    BODY_STYLE,
                ),
            ],
        ],
        colWidths=[
            45 * mm,
            125 * mm,
        ],
    )

    metadata.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#f1f5f9"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#e2e8f0"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    story.append(metadata)

    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            "Evaluation Scores",
            SECTION_STYLE,
        )
    )

    score_data = [
        [
            Paragraph(
                "Relevance",
                CENTER_STYLE,
            ),
            Paragraph(
                "Accuracy",
                CENTER_STYLE,
            ),
            Paragraph(
                "Hallucination Free",
                CENTER_STYLE,
            ),
            Paragraph(
                "Completeness",
                CENTER_STYLE,
            ),
            Paragraph(
                "Final Score",
                CENTER_STYLE,
            ),
        ],
        [
            Paragraph(
                score_percent(relevance),
                SCORE_STYLE,
            ),
            Paragraph(
                score_percent(accuracy),
                SCORE_STYLE,
            ),
            Paragraph(
                score_percent(hallucination_free),
                SCORE_STYLE,
            ),
            Paragraph(
                score_percent(completeness),
                SCORE_STYLE,
            ),
            Paragraph(
                score_percent(final_score),
                SCORE_STYLE,
            ),
        ],
    ]

    score_table = Table(
        score_data,
        colWidths=[
            34 * mm,
            34 * mm,
            34 * mm,
            34 * mm,
            34 * mm,
        ],
    )

    score_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#f1f5f9"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#e2e8f0"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
            ]
        )
    )

    story.append(score_table)

    # -----------------------------------------------------
    # Question
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Question",
            SECTION_STYLE,
        )
    )

    question_table = Table(
        [
            [
                Paragraph(
                    question,
                    BODY_STYLE,
                )
            ]
        ],
        colWidths=[
            170 * mm
        ],
    )

    question_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#f8fafc"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    colors.HexColor("#e2e8f0"),
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
            ]
        )
    )

    story.append(question_table)

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "AI Response",
            SECTION_STYLE,
        )
    )

    response_table = Table(
        [
            [
                Paragraph(
                    response,
                    BODY_STYLE,
                )
            ]
        ],
        colWidths=[
            170 * mm
        ],
    )

    response_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#f8fafc"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    colors.HexColor("#e2e8f0"),
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
            ]
        )
    )

    story.append(response_table)

    # -----------------------------------------------------
    # Reference
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Reference Answer",
            SECTION_STYLE,
        )
    )

    story.append(
        Paragraph(
            reference_answer,
            BODY_STYLE,
        )
    )

    # -----------------------------------------------------
    # Detailed analysis
    # -----------------------------------------------------

    story.append(PageBreak())

    story.append(
        Paragraph(
            "Detailed Dimension Analysis",
            SECTION_STYLE,
        )
    )

    dimensions = [
        (
            "Relevance",
            relevance,
            "relevance",
        ),
        (
            "Accuracy",
            accuracy,
            "accuracy",
        ),
        (
            "Hallucination Free",
            hallucination_free,
            "hallucination_free",
        ),
        (
            "Completeness",
            completeness,
            "completeness",
        ),
    ]

    for title, score, key in dimensions:

        block = []

        block.append(
            Paragraph(
                f"{title} — {score_percent(score)}",
                SECTION_STYLE,
            )
        )

        block.append(
            Paragraph(
                extract_explanation(
                    result,
                    key,
                ),
                BODY_STYLE,
            )
        )

        story.append(
            KeepTogether(block)
        )

    # -----------------------------------------------------
    # Hallucination
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Hallucination Analysis",
            SECTION_STYLE,
        )
    )

    hallucination_status = safe_value(
        get_field(
            hallucination,
            "status",
            "Not available",
        )
    )

    hallucination_explanation = safe_value(
        get_field(
            hallucination,
            "explanation",
            None,
        )
    )

    story.append(
        Paragraph(
            f"<b>Status:</b> "
            f"{hallucination_status}",
            BODY_STYLE,
        )
    )

    if hallucination_explanation != "Not available":

        story.append(
            Paragraph(
                hallucination_explanation,
                BODY_STYLE,
            )
        )

    flagged_claims = get_field(
        hallucination,
        "flagged_claims",
        [],
    ) or []

    if flagged_claims:

        story.append(
            Paragraph(
                "<b>Flagged Claims</b>",
                BODY_STYLE,
            )
        )

        claim_rows = [
            [
                Paragraph(
                    "Claim",
                    WHITE_BOLD_STYLE,
                ),
                Paragraph(
                    "Reason",
                    WHITE_BOLD_STYLE,
                ),
                Paragraph(
                    "Evidence",
                    WHITE_BOLD_STYLE,
                ),
            ]
        ]

        for claim in flagged_claims:

            claim_text = safe_value(
                get_field(
                    claim,
                    "claim",
                ),
                "N/A",
            )

            reason = safe_value(
                get_field(
                    claim,
                    "reason",
                ),
                "N/A",
            )

            evidence = safe_value(
                get_field(
                    claim,
                    "evidence",
                ),
                "N/A",
            )

            claim_rows.append(
                [
                    Paragraph(
                        claim_text,
                        SMALL_STYLE,
                    ),
                    Paragraph(
                        reason,
                        SMALL_STYLE,
                    ),
                    Paragraph(
                        evidence,
                        SMALL_STYLE,
                    ),
                ]
            )

        claim_table = Table(
            claim_rows,
            colWidths=[
                55 * mm,
                55 * mm,
                60 * mm,
            ],
            repeatRows=1,
        )

        claim_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#334155"),
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#cbd5e1"),
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                ]
            )
        )

        story.append(claim_table)

    else:

        story.append(
            Paragraph(
                "No flagged hallucination claims were reported.",
                BODY_STYLE,
            )
        )

    # -----------------------------------------------------
    # Completeness
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Completeness Analysis",
            SECTION_STYLE,
        )
    )

    completeness_analysis = get_field(
        result,
        "completeness_analysis",
        None,
    )

    completeness_status = safe_value(
        get_field(
            completeness_analysis,
            "status",
            "Not available",
        )
    )

    completeness_explanation = safe_value(
        get_field(
            completeness_analysis,
            "explanation",
            None,
        )
    )

    story.append(
        Paragraph(
            f"<b>Status:</b> "
            f"{completeness_status}",
            BODY_STYLE,
        )
    )

    if completeness_explanation != "Not available":

        story.append(
            Paragraph(
                completeness_explanation,
                BODY_STYLE,
            )
        )

    missing_aspects = get_field(
        completeness_analysis,
        "missing_aspects",
        [],
    ) or []

    missing_items = format_list(
        missing_aspects
    )

    if missing_items:

        story.append(
            Paragraph(
                "<b>Missing Information</b>",
                BODY_STYLE,
            )
        )

        for item in missing_items:

            story.append(
                Paragraph(
                    f"• {item}",
                    BODY_STYLE,
                )
            )

    else:

        story.append(
            Paragraph(
                "No missing information was reported.",
                BODY_STYLE,
            )
        )

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Consolidated Evaluation Summary",
            SECTION_STYLE,
        )
    )

    if consolidated_explanation:

        story.append(
            Paragraph(
                safe_value(
                    consolidated_explanation
                ),
                BODY_STYLE,
            )
        )

    else:

        story.append(
            Paragraph(
                "No consolidated explanation was provided.",
                BODY_STYLE,
            )
        )

    if recommendation:

        story.append(
            Paragraph(
                "<b>Recommendation</b>",
                BODY_STYLE,
            )
        )

        story.append(
            Paragraph(
                safe_value(
                    recommendation
                ),
                BODY_STYLE,
            )
        )

    # -----------------------------------------------------
    # Verdict
    # -----------------------------------------------------

    story.append(
        Spacer(1, 10)
    )

    verdict_table = Table(
        [
            [
                Paragraph(
                    f"FINAL VERDICT: {verdict}",
                    WHITE_BOLD_STYLE,
                ),
                Paragraph(
                    f"SCORE: "
                    f"{score_percent(final_score)}",
                    WHITE_BOLD_STYLE,
                ),
            ]
        ],
        colWidths=[
            100 * mm,
            70 * mm,
        ],
    )

    verdict_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#0f172a"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
            ]
        )
    )

    story.append(verdict_table)

    document.build(
        story,
        onFirstPage=draw_page,
        onLaterPages=draw_page,
    )

    buffer.seek(0)

    return buffer


# =========================================================
# BATCH EVALUATION PDF
# =========================================================

def build_batch_pdf(
    batch: Any,
) -> BytesIO:

    buffer = BytesIO()

    batch_id = safe_value(
        get_field(
            batch,
            "batch_id",
        ),
        "Unknown",
    )

    filename = safe_value(
        get_field(
            batch,
            "filename",
        ),
        "Batch Evaluation",
    )

    status = safe_value(
        get_field(
            batch,
            "status",
        ),
        "Unknown",
    )

    created_at = safe_value(
        get_field(
            batch,
            "created_at",
        ),
        "Not available",
    )

    items = find_batch_items(batch)

    stats = get_batch_statistics(
        batch,
        items,
    )

    document = create_document(
        buffer,
        "VALID Batch Evaluation Report",
    )

    story = []

    # =====================================================
    # TITLE
    # =====================================================

    story.append(
        Paragraph(
            "VALID Batch Evaluation Report",
            TITLE_STYLE,
        )
    )

    story.append(
        Paragraph(
            "AI Response Quality & Reliability Analysis",
            SUBTITLE_STYLE,
        )
    )

    # =====================================================
    # BATCH INFORMATION
    # =====================================================

    story.append(
        Paragraph(
            "Batch Information",
            SECTION_STYLE,
        )
    )

    metadata = Table(
        [
            [
                Paragraph(
                    "<b>Batch ID</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    batch_id,
                    BODY_STYLE,
                ),
            ],
            [
                Paragraph(
                    "<b>Dataset</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    filename,
                    BODY_STYLE,
                ),
            ],
            [
                Paragraph(
                    "<b>Status</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    status.upper(),
                    BODY_STYLE,
                ),
            ],
            [
                Paragraph(
                    "<b>Created</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    created_at,
                    BODY_STYLE,
                ),
            ],
        ],
        colWidths=[
            45 * mm,
            125 * mm,
        ],
    )

    metadata.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#f1f5f9"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#e2e8f0"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    story.append(metadata)

    # =====================================================
    # BATCH SUMMARY
    # =====================================================

    story.append(
        Paragraph(
            "Batch Summary",
            SECTION_STYLE,
        )
    )

    summary_data = [
        [
            Paragraph(
                "Total Responses",
                CENTER_STYLE,
            ),
            Paragraph(
                "Completed",
                CENTER_STYLE,
            ),
            Paragraph(
                "Failed",
                CENTER_STYLE,
            ),
            Paragraph(
                "Invalid",
                CENTER_STYLE,
            ),
            Paragraph(
                "Average Score",
                CENTER_STYLE,
            ),
        ],
        [
            Paragraph(
                str(stats["total"]),
                SCORE_STYLE,
            ),
            Paragraph(
                str(stats["completed"]),
                SCORE_STYLE,
            ),
            Paragraph(
                str(stats["failed"]),
                SCORE_STYLE,
            ),
            Paragraph(
                str(stats["invalid"]),
                SCORE_STYLE,
            ),
            Paragraph(
                score_percent(
                    stats["final_score"]
                ),
                SCORE_STYLE,
            ),
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[
            34 * mm,
            34 * mm,
            34 * mm,
            34 * mm,
            34 * mm,
        ],
    )

    summary_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#f1f5f9"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#e2e8f0"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
            ]
        )
    )

    story.append(summary_table)

    # =====================================================
    # DIMENSION BREAKDOWN
    # =====================================================

    story.append(
        Paragraph(
            "Average Dimension Scores",
            SECTION_STYLE,
        )
    )

    dimension_data = [
        [
            Paragraph(
                "Dimension",
                WHITE_BOLD_STYLE,
            ),
            Paragraph(
                "Average Score",
                WHITE_BOLD_STYLE,
            ),
        ],
        [
            Paragraph(
                "Relevance",
                BODY_STYLE,
            ),
            Paragraph(
                score_percent(
                    stats["relevance"]
                ),
                BODY_STYLE,
            ),
        ],
        [
            Paragraph(
                "Accuracy",
                BODY_STYLE,
            ),
            Paragraph(
                score_percent(
                    stats["accuracy"]
                ),
                BODY_STYLE,
            ),
        ],
        [
            Paragraph(
                "Hallucination Free",
                BODY_STYLE,
            ),
            Paragraph(
                score_percent(
                    stats["hallucination_free"]
                ),
                BODY_STYLE,
            ),
        ],
        [
            Paragraph(
                "Completeness",
                BODY_STYLE,
            ),
            Paragraph(
                score_percent(
                    stats["completeness"]
                ),
                BODY_STYLE,
            ),
        ],
        [
            Paragraph(
                "Final Score",
                BODY_STYLE,
            ),
            Paragraph(
                score_percent(
                    stats["final_score"]
                ),
                BODY_STYLE,
            ),
        ],
    ]

    dimension_table = Table(
        dimension_data,
        colWidths=[
            110 * mm,
            60 * mm,
        ],
    )

    dimension_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#334155"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#cbd5e1"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (1, -1),
                    "CENTER",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    story.append(dimension_table)

    # =====================================================
    # VERDICT DISTRIBUTION
    # =====================================================

    story.append(
        Paragraph(
            "Verdict Distribution",
            SECTION_STYLE,
        )
    )

    verdict_counts = stats[
        "verdict_counts"
    ]

    verdict_table_data = [
        [
            Paragraph(
                "Verdict",
                WHITE_BOLD_STYLE,
            ),
            Paragraph(
                "Count",
                WHITE_BOLD_STYLE,
            ),
        ],
        [
            Paragraph(
                "PASS",
                BODY_STYLE,
            ),
            Paragraph(
                str(
                    verdict_counts["PASS"]
                ),
                BODY_STYLE,
            ),
        ],
        [
            Paragraph(
                "NEEDS IMPROVEMENT",
                BODY_STYLE,
            ),
            Paragraph(
                str(
                    verdict_counts[
                        "NEEDS_IMPROVEMENT"
                    ]
                ),
                BODY_STYLE,
            ),
        ],
        [
            Paragraph(
                "FAIL",
                BODY_STYLE,
            ),
            Paragraph(
                str(
                    verdict_counts["FAIL"]
                ),
                BODY_STYLE,
            ),
        ],
    ]

    verdict_distribution_table = Table(
        verdict_table_data,
        colWidths=[
            110 * mm,
            60 * mm,
        ],
    )

    verdict_distribution_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#334155"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#cbd5e1"),
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (1, -1),
                    "CENTER",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    story.append(
        verdict_distribution_table
    )

    # =====================================================
    # HALLUCINATION
    # =====================================================

    story.append(
        Paragraph(
            "Hallucination Analysis",
            SECTION_STYLE,
        )
    )

    story.append(
        Paragraph(
            f"<b>Responses with detected "
            f"hallucination:</b> "
            f"{stats['hallucination_count']}",
            BODY_STYLE,
        )
    )

    story.append(
        Paragraph(
            "Hallucination frequency is calculated "
            "from the hallucination analysis attached "
            "to each evaluated response.",
            SMALL_STYLE,
        )
    )

    # =====================================================
    # FLAGGED RESPONSES
    # =====================================================

    story.append(PageBreak())

    story.append(
        Paragraph(
            "Flagged Responses",
            SECTION_STYLE,
        )
    )

    flagged_items = []

    for index, item in enumerate(
        items,
        start=1,
    ):

        verdict = safe_value(
            get_field(
                item,
                "verdict",
            ),
            "UNKNOWN",
        ).upper()

        final_score = score_value(
            get_field(
                item,
                "final_score",
                0,
            )
        )

        hallucination = get_field(
            item,
            "hallucination_analysis",
            None,
        )

        flagged_claims = get_field(
            hallucination,
            "flagged_claims",
            [],
        ) or []

        is_flagged = (
            verdict in {
                "FAIL",
                "FAILED",
                "POOR",
            }
            or bool(flagged_claims)
            or final_score < 0.5
        )

        if not is_flagged:
            continue

        question = safe_value(
            get_field(
                item,
                "question",
            ),
            f"Response {index}",
        )

        response_id = safe_value(
            get_field(
                item,
                "id",
            ),
            str(index),
        )

        issue_parts = []

        if flagged_claims:
            issue_parts.append(
                "Hallucination detected"
            )

        if final_score < 0.5:
            issue_parts.append(
                "Low overall score"
            )

        if verdict in {
            "FAIL",
            "FAILED",
            "POOR",
        }:
            issue_parts.append(
                "Failed evaluation"
            )

        issue = (
            "; ".join(issue_parts)
            if issue_parts
            else "Requires review"
        )

        flagged_items.append(
            [
                response_id,
                question,
                verdict,
                score_percent(final_score),
                issue,
            ]
        )

    if flagged_items:

        rows = [
            [
                Paragraph(
                    "ID",
                    WHITE_BOLD_STYLE,
                ),
                Paragraph(
                    "Question",
                    WHITE_BOLD_STYLE,
                ),
                Paragraph(
                    "Verdict",
                    WHITE_BOLD_STYLE,
                ),
                Paragraph(
                    "Score",
                    WHITE_BOLD_STYLE,
                ),
                Paragraph(
                    "Issue",
                    WHITE_BOLD_STYLE,
                ),
            ]
        ]

        for row in flagged_items:

            rows.append(
                [
                    Paragraph(
                        safe_value(
                            row[0]
                        ),
                        SMALL_STYLE,
                    ),
                    Paragraph(
                        safe_value(
                            row[1]
                        ),
                        SMALL_STYLE,
                    ),
                    Paragraph(
                        safe_value(
                            row[2]
                        ),
                        SMALL_STYLE,
                    ),
                    Paragraph(
                        safe_value(
                            row[3]
                        ),
                        SMALL_STYLE,
                    ),
                    Paragraph(
                        safe_value(
                            row[4]
                        ),
                        SMALL_STYLE,
                    ),
                ]
            )

        flagged_table = Table(
            rows,
            colWidths=[
                20 * mm,
                60 * mm,
                28 * mm,
                22 * mm,
                40 * mm,
            ],
            repeatRows=1,
        )

        flagged_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#334155"),
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#cbd5e1"),
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                ]
            )
        )

        story.append(flagged_table)

    else:

        story.append(
            Paragraph(
                "No flagged responses were identified.",
                BODY_STYLE,
            )
        )

    # =====================================================
    # IMPROVEMENT RECOMMENDATIONS
    # =====================================================

    story.append(
        Paragraph(
            "Improvement Recommendations",
            SECTION_STYLE,
        )
    )

    recommendations = []

    if stats["accuracy"] < 0.70:
        recommendations.append(
            "Improve factual accuracy and verify "
            "claims against reliable reference information."
        )

    if stats["hallucination_free"] < 0.70:
        recommendations.append(
            "Review hallucination-prone responses "
            "and strengthen factual grounding."
        )

    if stats["completeness"] < 0.70:
        recommendations.append(
            "Improve completeness by ensuring that "
            "important aspects of each question are addressed."
        )

    if stats["relevance"] < 0.70:
        recommendations.append(
            "Improve response relevance by keeping "
            "answers focused on the user's question."
        )

    if stats["final_score"] < 0.70:
        recommendations.append(
            "Review low-scoring responses and "
            "prioritize improvements across multiple dimensions."
        )

    if not recommendations:
        recommendations.append(
            "Overall quality is strong. Continue "
            "monitoring accuracy, completeness, relevance, "
            "and hallucination frequency."
        )

    for recommendation in recommendations:

        story.append(
            Paragraph(
                f"• {recommendation}",
                BODY_STYLE,
            )
        )

    # =====================================================
    # FINAL BATCH SUMMARY
    # =====================================================

    story.append(
        Spacer(1, 10)
    )

    final_batch_table = Table(
        [
            [
                Paragraph(
                    "BATCH EVALUATION COMPLETE",
                    WHITE_BOLD_STYLE,
                ),
                Paragraph(
                    f"AVERAGE SCORE: "
                    f"{score_percent(stats['final_score'])}",
                    WHITE_BOLD_STYLE,
                ),
            ]
        ],
        colWidths=[
            100 * mm,
            70 * mm,
        ],
    )

    final_batch_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#0f172a"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
            ]
        )
    )

    story.append(
        final_batch_table
    )

    document.build(
        story,
        onFirstPage=draw_page,
        onLaterPages=draw_page,
    )

    buffer.seek(0)

    return buffer


# =========================================================
# SINGLE PDF API
# =========================================================

@router.get(
    "/result/{evaluation_id}/pdf",
)
async def download_evaluation_pdf(
    evaluation_id: str,
):

    try:

        result = await get_result(
            evaluation_id
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to retrieve evaluation: "
                f"{exc}"
            ),
        )

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Evaluation not found.",
        )

    try:

        pdf_buffer = build_evaluation_pdf(
            result
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to generate PDF: "
                f"{exc}"
            ),
        )

    filename = (
        f"VALID_Evaluation_"
        f"{evaluation_id}.pdf"
    )

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; '
                f'filename="{filename}"'
            )
        },
    )


# =========================================================
# BATCH PDF API
# =========================================================

@router.get(
    "/batch/{batch_id}/pdf",
)
async def download_batch_pdf(
    batch_id: str,
):

    try:

        batch = await get_batch_result(
            batch_id
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to retrieve batch: "
                f"{exc}"
            ),
        )

    if batch is None:

        raise HTTPException(
            status_code=404,
            detail="Batch evaluation not found.",
        )

    try:

        pdf_buffer = build_batch_pdf(
            batch
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to generate batch PDF: "
                f"{exc}"
            ),
        )

    safe_batch_id = (
        str(batch_id)
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )

    filename = (
        f"VALID_Batch_Report_"
        f"{safe_batch_id}.pdf"
    )

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; '
                f'filename="{filename}"'
            )
        },
    )

# =========================================================
# BATCH PDF REPORT
# =========================================================

def build_batch_evaluation_pdf(batch: Any) -> BytesIO:
    buffer = BytesIO()

    batch_id = safe_value(
        get_field(batch, "batch_id"),
        "Unknown",
    )

    filename = safe_value(
        get_field(batch, "filename"),
        "Batch Evaluation",
    )

    total_rows = get_field(batch, "total_rows", 0) or 0
    valid_rows = get_field(batch, "valid_rows", 0) or 0
    invalid_rows = get_field(batch, "invalid_rows", 0) or 0
    completed_rows = get_field(batch, "completed_rows", 0) or 0
    failed_rows = get_field(batch, "failed_rows", 0) or 0

    status = safe_value(
        get_field(batch, "status"),
        "Unknown",
    )

    statistics = get_field(
        batch,
        "statistics",
        {},
    ) or {}

    average_relevance = score_value(
        get_field(
            statistics,
            "average_relevance",
            0,
        )
    )

    average_accuracy = score_value(
        get_field(
            statistics,
            "average_accuracy",
            0,
        )
    )

    average_hallucination_free = score_value(
        get_field(
            statistics,
            "average_hallucination_free",
            0,
        )
    )

    average_completeness = score_value(
        get_field(
            statistics,
            "average_completeness",
            0,
        )
    )

    average_final_score = score_value(
        get_field(
            statistics,
            "average_final_score",
            0,
        )
    )

    pass_count = get_field(
        statistics,
        "pass_count",
        0,
    ) or 0

    needs_improvement_count = get_field(
        statistics,
        "needs_improvement_count",
        0,
    ) or 0

    fail_count = get_field(
        statistics,
        "fail_count",
        0,
    ) or 0

    hallucination_count = get_field(
        statistics,
        "hallucination_count",
        0,
    ) or 0

    results = get_field(
        batch,
        "results",
        [],
    ) or []

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        title="VALI Batch Evaluation Report",
        author="VALI",
    )

    story = []

    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "VALI Batch Evaluation Report",
            TITLE_STYLE,
        )
    )

    story.append(
        Paragraph(
            "AI Response Quality & Reliability Analysis",
            SUBTITLE_STYLE,
        )
    )

    # -----------------------------------------------------
    # BATCH INFORMATION
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Batch Information",
            SECTION_STYLE,
        )
    )

    batch_info = Table(
        [
            [
                Paragraph(
                    "<b>Batch ID</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    batch_id,
                    BODY_STYLE,
                ),
            ],
            [
                Paragraph(
                    "<b>Dataset</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    filename,
                    BODY_STYLE,
                ),
            ],
            [
                Paragraph(
                    "<b>Status</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    status.upper(),
                    BODY_STYLE,
                ),
            ],
            [
                Paragraph(
                    "<b>Total Rows</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    str(total_rows),
                    BODY_STYLE,
                ),
            ],
            [
                Paragraph(
                    "<b>Valid Rows</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    str(valid_rows),
                    BODY_STYLE,
                ),
            ],
            [
                Paragraph(
                    "<b>Completed Rows</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    str(completed_rows),
                    BODY_STYLE,
                ),
            ],
            [
                Paragraph(
                    "<b>Failed Rows</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    str(failed_rows),
                    BODY_STYLE,
                ),
            ],
            [
                Paragraph(
                    "<b>Invalid Rows</b>",
                    BODY_STYLE,
                ),
                Paragraph(
                    str(invalid_rows),
                    BODY_STYLE,
                ),
            ],
        ],
        colWidths=[
            55 * mm,
            115 * mm,
        ],
    )

    batch_info.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#f1f5f9"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#e2e8f0"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    story.append(batch_info)

    # -----------------------------------------------------
    # QUALITY OVERVIEW
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Batch Quality Overview",
            SECTION_STYLE,
        )
    )

    score_data = [
        [
            Paragraph("Relevance", CENTER_STYLE),
            Paragraph("Accuracy", CENTER_STYLE),
            Paragraph(
                "Hallucination Free",
                CENTER_STYLE,
            ),
            Paragraph("Completeness", CENTER_STYLE),
            Paragraph("Final Score", CENTER_STYLE),
        ],
        [
            Paragraph(
                score_percent(
                    average_relevance
                ),
                SCORE_STYLE,
            ),
            Paragraph(
                score_percent(
                    average_accuracy
                ),
                SCORE_STYLE,
            ),
            Paragraph(
                score_percent(
                    average_hallucination_free
                ),
                SCORE_STYLE,
            ),
            Paragraph(
                score_percent(
                    average_completeness
                ),
                SCORE_STYLE,
            ),
            Paragraph(
                score_percent(
                    average_final_score
                ),
                SCORE_STYLE,
            ),
        ],
    ]

    score_table = Table(
        score_data,
        colWidths=[
            34 * mm,
            34 * mm,
            34 * mm,
            34 * mm,
            34 * mm,
        ],
    )

    score_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#f1f5f9"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#e2e8f0"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
            ]
        )
    )

    story.append(score_table)

    # -----------------------------------------------------
    # VERDICT DISTRIBUTION
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Verdict Distribution",
            SECTION_STYLE,
        )
    )

    verdict_table = Table(
        [
            [
                Paragraph(
                    "<b>PASS</b>",
                    CENTER_STYLE,
                ),
                Paragraph(
                    "<b>NEEDS IMPROVEMENT</b>",
                    CENTER_STYLE,
                ),
                Paragraph(
                    "<b>FAIL</b>",
                    CENTER_STYLE,
                ),
                Paragraph(
                    "<b>HALLUCINATION CASES</b>",
                    CENTER_STYLE,
                ),
            ],
            [
                Paragraph(
                    str(pass_count),
                    SCORE_STYLE,
                ),
                Paragraph(
                    str(
                        needs_improvement_count
                    ),
                    SCORE_STYLE,
                ),
                Paragraph(
                    str(fail_count),
                    SCORE_STYLE,
                ),
                Paragraph(
                    str(hallucination_count),
                    SCORE_STYLE,
                ),
            ],
        ],
        colWidths=[
            42.5 * mm,
            42.5 * mm,
            42.5 * mm,
            42.5 * mm,
        ],
    )

    verdict_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#f1f5f9"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#e2e8f0"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )

    story.append(verdict_table)

    # -----------------------------------------------------
    # RESPONSE DETAILS
    # -----------------------------------------------------

    story.append(PageBreak())

    story.append(
        Paragraph(
            "Evaluation Results",
            SECTION_STYLE,
        )
    )

    response_rows = [
        [
            Paragraph(
                "Row",
                WHITE_BOLD_STYLE,
            ),
            Paragraph(
                "Verdict",
                WHITE_BOLD_STYLE,
            ),
            Paragraph(
                "Score",
                WHITE_BOLD_STYLE,
            ),
            Paragraph(
                "Hallucination",
                WHITE_BOLD_STYLE,
            ),
        ]
    ]

    flagged_results = []

    for item in results:

        result = get_field(
            item,
            "result",
            None,
        )

        row_number = get_field(
            item,
            "row_number",
            "N/A",
        )

        item_status = safe_value(
            get_field(
                item,
                "status",
                "",
            ),
            "",
        )

        if result is None:

            response_rows.append(
                [
                    Paragraph(
                        str(row_number),
                        SMALL_STYLE,
                    ),
                    Paragraph(
                        item_status
                        or "FAILED",
                        SMALL_STYLE,
                    ),
                    Paragraph(
                        "N/A",
                        SMALL_STYLE,
                    ),
                    Paragraph(
                        "N/A",
                        SMALL_STYLE,
                    ),
                ]
            )

            continue

        item_verdict = safe_value(
            get_field(
                result,
                "verdict",
            ),
            "UNKNOWN",
        ).upper()

        item_score = score_percent(
            get_field(
                result,
                "final_score",
                0,
            )
        )

        item_hallucination = get_field(
            result,
            "hallucination_analysis",
            None,
        )

        hallucination_status = safe_value(
            get_field(
                item_hallucination,
                "status",
                "unknown",
            ),
            "unknown",
        ).lower()

        hallucination_label = (
            "YES"
            if hallucination_status
            in {
                "hallucination",
                "unsupported",
                "flagged",
                "detected",
            }
            else "NO"
        )

        response_rows.append(
            [
                Paragraph(
                    str(row_number),
                    SMALL_STYLE,
                ),
                Paragraph(
                    item_verdict,
                    SMALL_STYLE,
                ),
                Paragraph(
                    item_score,
                    SMALL_STYLE,
                ),
                Paragraph(
                    hallucination_label,
                    SMALL_STYLE,
                ),
            ]
        )

        if (
            hallucination_label == "YES"
            or item_verdict == "FAIL"
        ):
            flagged_results.append(
                (
                    row_number,
                    result,
                )
            )

    results_table = Table(
        response_rows,
        colWidths=[
            25 * mm,
            55 * mm,
            35 * mm,
            55 * mm,
        ],
        repeatRows=1,
    )

    results_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#334155"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#cbd5e1"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    story.append(results_table)

    # -----------------------------------------------------
    # FLAGGED RESPONSES
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Flagged Responses",
            SECTION_STYLE,
        )
    )

    if flagged_results:

        for row_number, result in flagged_results:

            verdict = safe_value(
                get_field(
                    result,
                    "verdict",
                ),
                "UNKNOWN",
            ).upper()

            final_score = score_percent(
                get_field(
                    result,
                    "final_score",
                    0,
                )
            )

            question = safe_value(
                get_field(
                    result,
                    "question",
                ),
                "Not available",
            )

            response = safe_value(
                get_field(
                    result,
                    "response",
                ),
                "Not available",
            )

            story.append(
                Paragraph(
                    f"Row {row_number} — "
                    f"{verdict} — "
                    f"{final_score}",
                    SECTION_STYLE,
                )
            )

            story.append(
                Paragraph(
                    f"<b>Question:</b> {question}",
                    BODY_STYLE,
                )
            )

            story.append(
                Paragraph(
                    f"<b>Response:</b> {response}",
                    BODY_STYLE,
                )
            )

            hallucination = get_field(
                result,
                "hallucination_analysis",
                None,
            )

            flagged_claims = get_field(
                hallucination,
                "flagged_claims",
                [],
            ) or []

            if flagged_claims:

                story.append(
                    Paragraph(
                        "<b>Flagged Claims:</b>",
                        BODY_STYLE,
                    )
                )

                for claim in flagged_claims:

                    claim_text = safe_value(
                        get_field(
                            claim,
                            "claim",
                        ),
                        "N/A",
                    )

                    reason = safe_value(
                        get_field(
                            claim,
                            "reason",
                        ),
                        "N/A",
                    )

                    evidence = safe_value(
                        get_field(
                            claim,
                            "evidence",
                        ),
                        "N/A",
                    )

                    story.append(
                        Paragraph(
                            f"• Claim: {claim_text}",
                            BODY_STYLE,
                        )
                    )

                    story.append(
                        Paragraph(
                            f"Reason: {reason}",
                            BODY_STYLE,
                        )
                    )

                    story.append(
                        Paragraph(
                            f"Evidence: {evidence}",
                            BODY_STYLE,
                        )
                    )

            recommendation = get_field(
                result,
                "recommendation",
                None,
            )

            if recommendation:

                story.append(
                    Paragraph(
                        "<b>Improvement Recommendation:</b>",
                        BODY_STYLE,
                    )
                )

                story.append(
                    Paragraph(
                        safe_value(
                            recommendation
                        ),
                        BODY_STYLE,
                    )
                )

            story.append(
                Spacer(1, 8)
            )

    else:

        story.append(
            Paragraph(
                "No failed or hallucination-flagged "
                "responses were reported.",
                BODY_STYLE,
            )
        )

    # -----------------------------------------------------
    # FINAL SUMMARY
    # -----------------------------------------------------

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            "Batch Evaluation Summary",
            SECTION_STYLE,
        )
    )

    if average_final_score >= 0.80:

        summary = (
            "The batch demonstrates strong overall "
            "response quality. Most evaluated responses "
            "meet the expected quality threshold."
        )

    elif average_final_score >= 0.60:

        summary = (
            "The batch demonstrates moderate response "
            "quality. Several responses may require "
            "additional review or improvement."
        )

    else:

        summary = (
            "The batch demonstrates low overall response "
            "quality. Significant improvement is "
            "recommended before deployment."
        )

    story.append(
        Paragraph(
            summary,
            BODY_STYLE,
        )
    )

    story.append(
        Paragraph(
            "<b>Improvement Recommendations</b>",
            SECTION_STYLE,
        )
    )

    recommendations = []

    if average_accuracy < 0.70:
        recommendations.append(
            "Improve factual accuracy by validating "
            "generated claims against reliable reference "
            "information."
        )

    if average_hallucination_free < 0.70:
        recommendations.append(
            "Strengthen hallucination detection and "
            "introduce grounding or verification steps "
            "for unsupported claims."
        )

    if average_completeness < 0.70:
        recommendations.append(
            "Improve completeness by ensuring that all "
            "important aspects of the reference answer "
            "are addressed."
        )

    if average_relevance < 0.70:
        recommendations.append(
            "Improve relevance by reducing unnecessary "
            "information and focusing responses on the "
            "user's question."
        )

    if not recommendations:
        recommendations.append(
            "Maintain the current evaluation quality and "
            "continue monitoring performance across new "
            "datasets."
        )

    for recommendation in recommendations:

        story.append(
            Paragraph(
                f"• {recommendation}",
                BODY_STYLE,
            )
        )

    # -----------------------------------------------------
    # FINAL VERDICT
    # -----------------------------------------------------

    if (
        fail_count > pass_count
        or average_final_score < 0.50
    ):
        overall_verdict = "REQUIRES IMPROVEMENT"

    elif (
        needs_improvement_count > pass_count
        or average_final_score < 0.70
    ):
        overall_verdict = "NEEDS IMPROVEMENT"

    else:
        overall_verdict = "PASS"

    story.append(
        Spacer(1, 12)
    )

    final_table = Table(
        [
            [
                Paragraph(
                    f"BATCH VERDICT: {overall_verdict}",
                    WHITE_BOLD_STYLE,
                ),
                Paragraph(
                    f"AVERAGE SCORE: "
                    f"{score_percent(average_final_score)}",
                    WHITE_BOLD_STYLE,
                ),
            ]
        ],
        colWidths=[
            100 * mm,
            70 * mm,
        ],
    )

    final_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#0f172a"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#0f172a"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
            ]
        )
    )

    story.append(final_table)

    document.build(
        story,
        onFirstPage=draw_page,
        onLaterPages=draw_page,
    )

    buffer.seek(0)

    return buffer


# =========================================================
# BATCH PDF API ENDPOINT
# =========================================================

@router.get(
    "/batch/{batch_id}/pdf",
)
async def download_batch_evaluation_pdf(
    batch_id: str,
):
    try:
        batch = await get_batch_result(
            batch_id
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to retrieve batch: {exc}"
            ),
        )

    if batch is None:
        raise HTTPException(
            status_code=404,
            detail="Batch evaluation not found.",
        )

    try:
        pdf_buffer = build_batch_evaluation_pdf(
            batch
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to generate batch PDF: {exc}"
            ),
        )

    filename = (
        f"VALI_Batch_{batch_id}.pdf"
    )

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )