import csv
import io
from statistics import mean
from typing import Any

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.responses import StreamingResponse

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.models.schemas import (
    BatchEvaluationItem,
    BatchEvaluationResult,
    BatchInvalidRow,
    BatchStatistics,
    EvaluationRequest,
    EvaluationResult,
    HistoryDetail,
    HistoryResponse,
    HistoryItem,
)

from backend.evaluation.orchestrator import Orchestrator

from backend.database.database import (
    save_result,
    get_result,
    save_batch_result,
    get_batch_result,
    get_history,
    get_history_detail,
)


router = APIRouter(
    prefix="/api/evaluation",
    tags=["Evaluation"],
)


# =========================================================
# ORCHESTRATOR
# =========================================================

_orchestrator: Orchestrator | None = None


def _get_orchestrator() -> Orchestrator:

    global _orchestrator

    if _orchestrator is None:
        _orchestrator = Orchestrator()

    return _orchestrator


# =========================================================
# SINGLE EVALUATION
# =========================================================

@router.post(
    "/submit",
    response_model=EvaluationResult,
)
async def submit_evaluation(
    request: EvaluationRequest,
):

    try:

        result = await _get_orchestrator().run(
            request
        )

    except Exception as e:

        raise HTTPException(
            status_code=503,
            detail=f"Evaluation failed: {str(e)}",
        )

    await save_result(result)

    return result


# =========================================================
# GET SINGLE EVALUATION
# =========================================================

@router.get(
    "/result/{evaluation_id}",
    response_model=EvaluationResult,
)
async def get_evaluation(
    evaluation_id: str,
):

    result = await get_result(
        evaluation_id
    )

    if not result:

        raise HTTPException(
            status_code=404,
            detail="Evaluation not found",
        )

    return result


# =========================================================
# PDF HELPERS
# =========================================================

def _clean_text(value: Any) -> str:

    if value is None:
        return ""

    if isinstance(value, (list, tuple)):

        return ", ".join(
            _clean_text(item)
            for item in value
        )

    if isinstance(value, dict):

        return "; ".join(
            f"{key}: {_clean_text(item)}"
            for key, item in value.items()
        )

    return str(value)


def _safe_float(value: Any) -> float:

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _score_percentage(value: Any) -> str:

    score = _safe_float(value)

    return f"{score * 100:.1f}%"


def _display_verdict(value: Any) -> str:

    verdict = str(
        value or "UNKNOWN"
    ).strip().upper()

    return verdict.replace(
        "_",
        " ",
    )


def _safe_filename(value: str) -> str:

    allowed = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789-_"
    )

    result = ""

    for char in value:

        if char in allowed:
            result += char
        else:
            result += "_"

    return result[:80] or "evaluation"


def _model_dump(result: EvaluationResult) -> dict:

    try:

        return result.model_dump(
            mode="json"
        )

    except Exception:

        try:

            return result.dict()

        except Exception:

            return {}


def _score_from_result(
    result: EvaluationResult,
    name: str,
) -> float:

    try:

        return _safe_float(
            getattr(
                result.scores,
                name,
                0,
            )
        )

    except Exception:

        return 0.0


def _analysis_value(
    analysis: Any,
    field: str,
) -> str:

    if not analysis:
        return ""

    try:

        value = getattr(
            analysis,
            field,
            None,
        )

        return _clean_text(
            value
        )

    except Exception:

        return ""


# =========================================================
# PDF STYLES
# =========================================================

def _pdf_styles():

    styles = getSampleStyleSheet()

    return {

        "title": ParagraphStyle(
            "VALITitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#111827"
            ),
            spaceAfter=5,
        ),

        "subtitle": ParagraphStyle(
            "VALISubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#6B7280"
            ),
            spaceAfter=18,
        ),

        "section": ParagraphStyle(
            "VALISection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor(
                "#111827"
            ),
            spaceBefore=14,
            spaceAfter=8,
        ),

        "body": ParagraphStyle(
            "VALIBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=14,
            textColor=colors.HexColor(
                "#374151"
            ),
            spaceAfter=5,
        ),

        "question": ParagraphStyle(
            "VALIQuestion",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=colors.HexColor(
                "#111827"
            ),
            spaceAfter=5,
        ),

        "small": ParagraphStyle(
            "VALISmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor(
                "#6B7280"
            ),
        ),
    }


# =========================================================
# SCORE TABLE
# =========================================================

def _build_score_table(
    result: EvaluationResult,
):

    styles = _pdf_styles()

    rows = [
        (
            "Relevance",
            _score_from_result(
                result,
                "relevance",
            ),
        ),
        (
            "Accuracy",
            _score_from_result(
                result,
                "accuracy",
            ),
        ),
        (
            "Hallucination-Free",
            _score_from_result(
                result,
                "hallucination_free",
            ),
        ),
        (
            "Completeness",
            _score_from_result(
                result,
                "completeness",
            ),
        ),
        (
            "Final Score",
            _safe_float(
                result.final_score
            ),
        ),
    ]

    data = [
        [
            Paragraph(
                "<b>Dimension</b>",
                styles["body"],
            ),
            Paragraph(
                "<b>Score</b>",
                styles["body"],
            ),
            Paragraph(
                "<b>Percentage</b>",
                styles["body"],
            ),
        ]
    ]

    for name, score in rows:

        data.append(
            [
                Paragraph(
                    name,
                    styles["body"],
                ),
                Paragraph(
                    f"{score:.4f}",
                    styles["body"],
                ),
                Paragraph(
                    f"{score * 100:.1f}%",
                    styles["body"],
                ),
            ]
        )

    table = Table(
        data,
        colWidths=[
            75 * mm,
            45 * mm,
            45 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#111827"
                    ),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(
                        "#D1D5DB"
                    ),
                ),
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, -1),
                    colors.HexColor(
                        "#F9FAFB"
                    ),
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

    return table


# =========================================================
# PDF GENERATOR
# =========================================================

def _build_pdf(
    result: EvaluationResult,
) -> io.BytesIO:

    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="VALI Evaluation Report",
        author="VALI",
    )

    styles = _pdf_styles()

    story = []

    # -----------------------------------------------------
    # HEADER
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "VALI",
            styles["title"],
        )
    )

    story.append(
        Paragraph(
            "AI Response Validation & LLM Evaluation Report",
            styles["subtitle"],
        )
    )

    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor(
                "#D1D5DB"
            ),
            spaceAfter=14,
        )
    )

    # -----------------------------------------------------
    # EVALUATION INFORMATION
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Evaluation Information",
            styles["section"],
        )
    )

    info = [
        [
            Paragraph(
                "<b>Evaluation ID</b>",
                styles["body"],
            ),
            Paragraph(
                _clean_text(result.id),
                styles["body"],
            ),
        ],
        [
            Paragraph(
                "<b>Verdict</b>",
                styles["body"],
            ),
            Paragraph(
                _display_verdict(
                    result.verdict
                ),
                styles["body"],
            ),
        ],
        [
            Paragraph(
                "<b>Final Score</b>",
                styles["body"],
            ),
            Paragraph(
                _score_percentage(
                    result.final_score
                ),
                styles["body"],
            ),
        ],
    ]

    info_table = Table(
        info,
        colWidths=[
            45 * mm,
            120 * mm,
        ],
    )

    info_table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(
                        "#D1D5DB"
                    ),
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor(
                        "#F3F4F6"
                    ),
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

    story.append(info_table)

    # -----------------------------------------------------
    # QUESTION
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Question",
            styles["section"],
        )
    )

    story.append(
        Paragraph(
            _clean_text(
                result.question
            ).replace(
                "\n",
                "<br/>",
            ),
            styles["question"],
        )
    )

    # -----------------------------------------------------
    # AI RESPONSE
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "AI Response",
            styles["section"],
        )
    )

    story.append(
        Paragraph(
            _clean_text(
                result.response
            ).replace(
                "\n",
                "<br/>",
            ),
            styles["body"],
        )
    )

    # -----------------------------------------------------
    # REFERENCE ANSWER
    # -----------------------------------------------------

    model_data = _model_dump(
        result
    )

    reference_answer = (
        model_data.get(
            "reference_answer"
        )
        or ""
    )

    if reference_answer:

        story.append(
            Paragraph(
                "Reference Answer",
                styles["section"],
            )
        )

        story.append(
            Paragraph(
                _clean_text(
                    reference_answer
                ).replace(
                    "\n",
                    "<br/>",
                ),
                styles["body"],
            )
        )

    # -----------------------------------------------------
    # SCORE BREAKDOWN
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Score Breakdown",
            styles["section"],
        )
    )

    story.append(
        _build_score_table(
            result
        )
    )

    # -----------------------------------------------------
    # HALLUCINATION
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Hallucination Analysis",
            styles["section"],
        )
    )

    hallucination = (
        result.hallucination_analysis
    )

    hallucination_status = (
        _analysis_value(
            hallucination,
            "status",
        )
        or "Unknown"
    )

    flagged_claims = []

    if hallucination:

        flagged_claims = (
            getattr(
                hallucination,
                "flagged_claims",
                None,
            )
            or []
        )

    hallucination_table = Table(
        [
            [
                Paragraph(
                    "<b>Status</b>",
                    styles["body"],
                ),
                Paragraph(
                    hallucination_status
                    .replace(
                        "_",
                        " ",
                    )
                    .title(),
                    styles["body"],
                ),
            ],
            [
                Paragraph(
                    "<b>Flagged Claims</b>",
                    styles["body"],
                ),
                Paragraph(
                    str(
                        len(
                            flagged_claims
                        )
                    ),
                    styles["body"],
                ),
            ],
        ],
        colWidths=[
            55 * mm,
            110 * mm,
        ],
    )

    hallucination_table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(
                        "#D1D5DB"
                    ),
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor(
                        "#F3F4F6"
                    ),
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

    story.append(
        hallucination_table
    )

    if flagged_claims:

        story.append(
            Spacer(
                1,
                7,
            )
        )

        story.append(
            Paragraph(
                "<b>Flagged Claims</b>",
                styles["body"],
            )
        )

        for index, claim in enumerate(
            flagged_claims,
            start=1,
        ):

            story.append(
                Paragraph(
                    f"{index}. "
                    f"{_clean_text(claim)}",
                    styles["body"],
                )
            )

    hallucination_explanation = (
        _analysis_value(
            hallucination,
            "explanation",
        )
    )

    if hallucination_explanation:

        story.append(
            Paragraph(
                "<b>Analysis</b>",
                styles["body"],
            )
        )

        story.append(
            Paragraph(
                hallucination_explanation.replace(
                    "\n",
                    "<br/>",
                ),
                styles["body"],
            )
        )

    # -----------------------------------------------------
    # COMPLETENESS
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "Completeness Analysis",
            styles["section"],
        )
    )

    completeness = (
        result.completeness_analysis
    )

    missing_aspects = []

    if completeness:

        missing_aspects = (
            getattr(
                completeness,
                "missing_aspects",
                None,
            )
            or []
        )

    completeness_table = Table(
        [
            [
                Paragraph(
                    "<b>Missing Aspects</b>",
                    styles["body"],
                ),
                Paragraph(
                    str(
                        len(
                            missing_aspects
                        )
                    ),
                    styles["body"],
                ),
            ]
        ],
        colWidths=[
            55 * mm,
            110 * mm,
        ],
    )

    completeness_table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(
                        "#D1D5DB"
                    ),
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor(
                        "#F3F4F6"
                    ),
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

    story.append(
        completeness_table
    )

    if missing_aspects:

        story.append(
            Spacer(
                1,
                7,
            )
        )

        story.append(
            Paragraph(
                "<b>Missing Information</b>",
                styles["body"],
            )
        )

        for index, aspect in enumerate(
            missing_aspects,
            start=1,
        ):

            story.append(
                Paragraph(
                    f"{index}. "
                    f"{_clean_text(aspect)}",
                    styles["body"],
                )
            )

    completeness_explanation = (
        _analysis_value(
            completeness,
            "explanation",
        )
    )

    if completeness_explanation:

        story.append(
            Paragraph(
                "<b>Analysis</b>",
                styles["body"],
            )
        )

        story.append(
            Paragraph(
                completeness_explanation.replace(
                    "\n",
                    "<br/>",
                ),
                styles["body"],
            )
        )

    # -----------------------------------------------------
    # EXTRA ANALYSIS
    # -----------------------------------------------------

    analysis_fields = [
        (
            "Relevance Analysis",
            "relevance_analysis",
        ),
        (
            "Accuracy Analysis",
            "accuracy_analysis",
        ),
        (
            "Overall Explanation",
            "explanation",
        ),
        (
            "Recommendation",
            "recommendation",
        ),
    ]

    for title, field in analysis_fields:

        value = model_data.get(
            field
        )

        if not value:
            continue

        story.append(
            Paragraph(
                title,
                styles["section"],
            )
        )

        if isinstance(
            value,
            dict,
        ):

            for key, item in value.items():

                text_value = _clean_text(
                    item
                )

                if not text_value:
                    continue

                story.append(
                    Paragraph(
                        (
                            f"<b>"
                            f"{_clean_text(key)}"
                            f".replace('_', ' ')"
                            f".title()"
                            f":</b> "
                            f"{text_value}"
                        ).replace(
                            "\n",
                            "<br/>",
                        ),
                        styles["body"],
                    )
                )

        else:

            story.append(
                Paragraph(
                    _clean_text(
                        value
                    ).replace(
                        "\n",
                        "<br/>",
                    ),
                    styles["body"],
                )
            )

    # -----------------------------------------------------
    # FOOTER
    # -----------------------------------------------------

    story.append(
        Spacer(
            1,
            18,
        )
    )

    story.append(
        HRFlowable(
            width="100%",
            thickness=0.7,
            color=colors.HexColor(
                "#D1D5DB"
            ),
        )
    )

    story.append(
        Spacer(
            1,
            6,
        )
    )

    story.append(
        Paragraph(
            "Generated by VALI — AI Response Validation & LLM Evaluation Platform",
            styles["small"],
        )
    )

    story.append(
        Paragraph(
            "This report summarizes automated LLM-as-a-Judge evaluation results.",
            styles["small"],
        )
    )

    document.build(
        story
    )

    buffer.seek(0)

    return buffer


# =========================================================
# M4.2 PDF REPORT ENDPOINT
# =========================================================

@router.get(
    "/report/{evaluation_id}",
)
async def generate_evaluation_report(
    evaluation_id: str,
):

    result = await get_result(
        evaluation_id
    )

    if not result:

        raise HTTPException(
            status_code=404,
            detail="Evaluation not found",
        )

    try:

        pdf_buffer = _build_pdf(
            result
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to generate PDF report: "
                f"{str(e)}"
            ),
        )

    filename = (
        "VALI_Evaluation_Report_"
        f"{_safe_filename(evaluation_id)}"
        ".pdf"
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


# =========================================================
# BATCH EVALUATION
# =========================================================

REQUIRED_COLUMNS = {
    "question",
    "response",
}

OPTIONAL_COLUMNS = {
    "reference_answer",
    "source",
    "source_document",
}


def _clean(value) -> str:

    if value is None:
        return ""

    return str(value).strip()


def _calculate_statistics(
    results: list[EvaluationResult],
) -> BatchStatistics:

    if not results:
        return BatchStatistics()

    relevance_scores = [
        result.scores.relevance
        for result in results
    ]

    accuracy_scores = [
        result.scores.accuracy
        for result in results
    ]

    hallucination_scores = [
        result.scores.hallucination_free
        for result in results
    ]

    completeness_scores = [
        result.scores.completeness
        for result in results
    ]

    final_scores = [
        result.final_score
        for result in results
    ]

    pass_count = sum(
        1
        for result in results
        if result.verdict == "PASS"
    )

    needs_improvement_count = sum(
        1
        for result in results
        if result.verdict
        == "NEEDS_IMPROVEMENT"
    )

    fail_count = sum(
        1
        for result in results
        if result.verdict == "FAIL"
    )

    hallucination_count = sum(
        1
        for result in results
        if (
            result.hallucination_analysis
            and result.hallucination_analysis.status
            not in {
                "supported",
                "unknown",
            }
        )
    )

    return BatchStatistics(
        average_relevance=round(
            mean(relevance_scores),
            4,
        ),
        average_accuracy=round(
            mean(accuracy_scores),
            4,
        ),
        average_hallucination_free=round(
            mean(hallucination_scores),
            4,
        ),
        average_completeness=round(
            mean(completeness_scores),
            4,
        ),
        average_final_score=round(
            mean(final_scores),
            4,
        ),
        pass_count=pass_count,
        needs_improvement_count=(
            needs_improvement_count
        ),
        fail_count=fail_count,
        hallucination_count=(
            hallucination_count
        ),
    )


@router.post(
    "/batch",
    response_model=BatchEvaluationResult,
)
async def batch_evaluation(
    file: UploadFile = File(...),
):

    filename = file.filename or ""

    if not filename.lower().endswith(
        ".csv"
    ):

        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported.",
        )

    try:

        contents = await file.read()

        text = contents.decode(
            "utf-8-sig"
        )

        csv_file = io.StringIO(text)

        reader = csv.DictReader(
            csv_file
        )

    except UnicodeDecodeError:

        raise HTTPException(
            status_code=400,
            detail="CSV must use UTF-8 encoding.",
        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to read CSV file: "
                f"{str(e)}"
            ),
        )

    if not reader.fieldnames:

        raise HTTPException(
            status_code=400,
            detail=(
                "CSV file is empty or has "
                "no header row."
            ),
        )

    headers = {
        header.strip().lower()
        for header in reader.fieldnames
        if header
    }

    missing_columns = (
        REQUIRED_COLUMNS - headers
    )

    if missing_columns:

        raise HTTPException(
            status_code=400,
            detail=(
                "Missing required CSV columns: "
                + ", ".join(
                    sorted(missing_columns)
                )
            ),
        )

    batch = BatchEvaluationResult(
        filename=filename,
        status="processing",
    )

    valid_results: list[
        EvaluationResult
    ] = []

    row_number = 1

    for raw_row in reader:

        row_number += 1

        row = {}

        for key, value in raw_row.items():

            if key is None:
                continue

            normalized_key = (
                key.strip().lower()
            )

            row[
                normalized_key
            ] = _clean(value)

        batch.total_rows += 1

        question = row.get(
            "question",
            "",
        )

        response = row.get(
            "response",
            "",
        )

        row_errors = []

        if not question:

            row_errors.append(
                "Missing question."
            )

        if not response:

            row_errors.append(
                "Missing response."
            )

        if row_errors:

            batch.invalid_rows += 1

            batch.invalid_row_details.append(
                BatchInvalidRow(
                    row_number=row_number,
                    error=" ".join(
                        row_errors
                    ),
                    data=row,
                )
            )

            continue

        batch.valid_rows += 1

        reference_answer = (
            row.get(
                "reference_answer"
            )
            or None
        )

        source_document = (
            row.get(
                "source_document"
            )
            or row.get(
                "source"
            )
            or None
        )

        request = EvaluationRequest(
            question=question,
            response=response,
            reference_answer=(
                reference_answer
            ),
            source_document=(
                source_document
            ),
        )

        try:

            result = await (
                _get_orchestrator().run(
                    request
                )
            )

            await save_result(
                result
            )

            valid_results.append(
                result
            )

            batch.completed_rows += 1

            batch.results.append(
                BatchEvaluationItem(
                    row_number=row_number,
                    evaluation_id=result.id,
                    question=result.question,
                    response=result.response,
                    result=result,
                    status="completed",
                )
            )

        except Exception as e:

            batch.failed_rows += 1

            batch.results.append(
                BatchEvaluationItem(
                    row_number=row_number,
                    question=question,
                    response=response,
                    status="failed",
                    error=str(e),
                )
            )

    batch.statistics = (
        _calculate_statistics(
            valid_results
        )
    )

    if batch.total_rows == 0:

        batch.status = "empty"

    elif (
        batch.completed_rows
        == batch.valid_rows
    ):

        if batch.invalid_rows > 0:

            batch.status = (
                "completed_with_errors"
            )

        else:

            batch.status = "completed"

    elif batch.completed_rows > 0:

        batch.status = (
            "partially_completed"
        )

    else:

        batch.status = "failed"

    await save_batch_result(
        batch
    )

    return batch


# =========================================================
# HISTORY
# =========================================================

@router.get(
    "/history",
    response_model=HistoryResponse,
)
async def evaluation_history():

    items = await get_history()

    return HistoryResponse(
        items=[
            HistoryItem(**item)
            for item in items
        ]
    )


@router.get(
    "/history/{history_id}",
    response_model=HistoryDetail,
)
async def evaluation_history_detail(
    history_id: str,
):

    detail = await get_history_detail(
        history_id
    )

    if not detail:

        raise HTTPException(
            status_code=404,
            detail="History item not found",
        )

    return HistoryDetail(
        **detail
    )


@router.get(
    "/batch/{batch_id}",
    response_model=BatchEvaluationResult,
)
async def get_historical_batch(
    batch_id: str,
):

    batch = await get_batch_result(
        batch_id
    )

    if not batch:

        raise HTTPException(
            status_code=404,
            detail="Batch evaluation not found",
        )

    return batch