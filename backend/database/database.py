import json
import os
from datetime import datetime, timezone

from sqlalchemy import Float, String, Text, select, text
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from backend.models.schemas import (
    AgentExplanations,
    AgentScores,
    BatchEvaluationResult,
    CompletenessAnalysis,
    EvaluationResult,
    HallucinationAnalysis,
)


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./data/evaluations.db",
)


# =========================================================
# DATABASE DIRECTORY
# =========================================================

if DATABASE_URL.startswith(
    "sqlite+aiosqlite:///./"
):
    os.makedirs(
        "./data",
        exist_ok=True,
    )


# =========================================================
# DATABASE ENGINE
# =========================================================

engine = create_async_engine(
    DATABASE_URL,
)

SessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


# =========================================================
# BASE
# =========================================================

class Base(DeclarativeBase):
    pass


# =========================================================
# SINGLE EVALUATION RECORD
# =========================================================

class EvaluationRecord(Base):

    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )

    question: Mapped[str] = mapped_column(
        Text,
    )

    response: Mapped[str] = mapped_column(
        Text,
    )

    scores: Mapped[str] = mapped_column(
        Text,
    )

    explanations: Mapped[str] = mapped_column(
        Text,
        default="{}",
    )

    completeness_analysis: Mapped[str] = mapped_column(
        Text,
        default="{}",
    )

    hallucination_analysis: Mapped[str] = mapped_column(
        Text,
        default="null",
    )

    final_score: Mapped[float] = mapped_column(
        Float,
    )

    verdict: Mapped[str] = mapped_column(
        String,
    )

    result_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[str] = mapped_column(
        String,
        default=lambda: datetime.now(
            timezone.utc
        ).isoformat(),
    )


# =========================================================
# BATCH HISTORY RECORD
# =========================================================

class BatchHistoryRecord(Base):

    __tablename__ = "batch_history"

    batch_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )

    filename: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    total_rows: Mapped[int] = mapped_column(
        default=0,
    )

    completed_rows: Mapped[int] = mapped_column(
        default=0,
    )

    failed_rows: Mapped[int] = mapped_column(
        default=0,
    )

    invalid_rows: Mapped[int] = mapped_column(
        default=0,
    )

    average_final_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
    )

    status: Mapped[str] = mapped_column(
        String,
        default="completed",
    )

    batch_json: Mapped[str] = mapped_column(
        Text,
    )

    created_at: Mapped[str] = mapped_column(
        String,
        default=lambda: datetime.now(
            timezone.utc
        ).isoformat(),
    )


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

async def init_db() -> None:

    async with engine.begin() as conn:

        await conn.run_sync(
            Base.metadata.create_all
        )

        # -------------------------------------------------
        # SQLite migrations
        # -------------------------------------------------

        if DATABASE_URL.startswith(
            "sqlite+aiosqlite"
        ):

            result = await conn.execute(
                text(
                    "PRAGMA table_info(evaluations)"
                )
            )

            existing_columns = {
                row[1]
                for row in result.fetchall()
            }

            migrations = {

                "completeness_analysis":
                    """
                    ALTER TABLE evaluations
                    ADD COLUMN completeness_analysis
                    TEXT DEFAULT '{}'
                    """,

                "hallucination_analysis":
                    """
                    ALTER TABLE evaluations
                    ADD COLUMN hallucination_analysis
                    TEXT DEFAULT 'null'
                    """,

                "result_json":
                    """
                    ALTER TABLE evaluations
                    ADD COLUMN result_json TEXT
                    """,

                "created_at":
                    """
                    ALTER TABLE evaluations
                    ADD COLUMN created_at TEXT
                    """,
            }

            for (
                column,
                statement,
            ) in migrations.items():

                if column not in existing_columns:

                    await conn.execute(
                        text(statement)
                    )


# =========================================================
# SAVE SINGLE EVALUATION
# =========================================================

async def save_result(
    result: EvaluationResult,
) -> None:

    async with SessionLocal() as session:

        record = EvaluationRecord(

            id=result.id,

            question=result.question,

            response=result.response,

            scores=(
                result.scores.model_dump_json()
            ),

            explanations=(
                result.explanations.model_dump_json()
            ),

            completeness_analysis=(
                result.completeness_analysis
                .model_dump_json()
            ),

            hallucination_analysis=(
                result.hallucination_analysis
                .model_dump_json()
                if result.hallucination_analysis
                else "null"
            ),

            final_score=result.final_score,

            verdict=result.verdict,

            result_json=(
                result.model_dump_json()
            ),

            created_at=datetime.now(
                timezone.utc
            ).isoformat(),
        )

        session.add(record)

        await session.commit()


# =========================================================
# GET SINGLE EVALUATION
# =========================================================

async def get_result(
    evaluation_id: str,
) -> EvaluationResult | None:

    async with SessionLocal() as session:

        row = await session.get(
            EvaluationRecord,
            evaluation_id,
        )

        if not row:
            return None

        # -------------------------------------------------
        # New records
        # -------------------------------------------------

        if row.result_json:

            return EvaluationResult.model_validate(
                json.loads(
                    row.result_json
                )
            )

        # -------------------------------------------------
        # Backward compatibility
        # -------------------------------------------------

        completeness_data = json.loads(
            row.completeness_analysis
            or "{}"
        )

        hallucination_data = json.loads(
            row.hallucination_analysis
            or "null"
        )

        return EvaluationResult(

            id=row.id,

            question=row.question,

            response=row.response,

            scores=AgentScores(
                **json.loads(
                    row.scores
                )
            ),

            explanations=AgentExplanations(
                **json.loads(
                    row.explanations
                    or "{}"
                )
            ),

            completeness_analysis=(
                CompletenessAnalysis(
                    **completeness_data
                )
            ),

            hallucination_analysis=(
                HallucinationAnalysis(
                    **hallucination_data
                )
                if hallucination_data
                else None
            ),

            final_score=row.final_score,

            verdict=row.verdict,
        )


# =========================================================
# SAVE BATCH EVALUATION
# =========================================================

async def save_batch_result(
    batch: BatchEvaluationResult,
) -> None:

    async with SessionLocal() as session:

        record = BatchHistoryRecord(

            batch_id=batch.batch_id,

            filename=batch.filename,

            total_rows=batch.total_rows,

            completed_rows=batch.completed_rows,

            failed_rows=batch.failed_rows,

            invalid_rows=batch.invalid_rows,

            average_final_score=(
                batch.statistics.average_final_score
            ),

            status=batch.status,

            batch_json=(
                batch.model_dump_json()
            ),

            created_at=datetime.now(
                timezone.utc
            ).isoformat(),
        )

        session.add(record)

        await session.commit()


# =========================================================
# GET BATCH EVALUATION
# =========================================================

async def get_batch_result(
    batch_id: str,
) -> BatchEvaluationResult | None:

    async with SessionLocal() as session:

        row = await session.get(
            BatchHistoryRecord,
            batch_id,
        )

        if not row:
            return None

        return BatchEvaluationResult.model_validate(
            json.loads(
                row.batch_json
            )
        )


# =========================================================
# EVALUATION HISTORY
# =========================================================

async def get_history() -> list[dict]:

    async with SessionLocal() as session:

        # -------------------------------------------------
        # Single evaluations
        # -------------------------------------------------

        evaluation_query = (
            select(EvaluationRecord)
            .order_by(
                EvaluationRecord.created_at.desc()
            )
        )

        evaluation_result = (
            await session.execute(
                evaluation_query
            )
        )

        evaluations = (
            evaluation_result
            .scalars()
            .all()
        )

        # -------------------------------------------------
        # Batch evaluations
        # -------------------------------------------------

        batch_query = (
            select(BatchHistoryRecord)
            .order_by(
                BatchHistoryRecord.created_at.desc()
            )
        )

        batch_result = (
            await session.execute(
                batch_query
            )
        )

        batches = (
            batch_result
            .scalars()
            .all()
        )

        # -------------------------------------------------
        # Build history
        # -------------------------------------------------

        history: list[dict] = []

        # -------------------------------------------------
        # Single history
        # -------------------------------------------------

        for row in evaluations:

            history.append(
                {
                    "id": row.id,

                    "type": "single",

                    "created_at": (
                        row.created_at or ""
                    ),

                    "title": (
                        "Single Evaluation"
                    ),

                    "question": (
                        row.question
                    ),

                    "final_score": (
                        row.final_score
                    ),

                    "verdict": (
                        row.verdict
                    ),
                }
            )

        # -------------------------------------------------
        # Batch history
        # -------------------------------------------------

        for row in batches:

            history.append(
                {
                    "id": row.batch_id,

                    "type": "batch",

                    "created_at": (
                        row.created_at or ""
                    ),

                    "title": (
                        row.filename
                        or "Batch Evaluation"
                    ),

                    "question": None,

                    "final_score": (
                        row.average_final_score
                    ),

                    "verdict": None,

                    "total_rows": (
                        row.total_rows
                    ),

                    "completed_rows": (
                        row.completed_rows
                    ),

                    "failed_rows": (
                        row.failed_rows
                    ),

                    "invalid_rows": (
                        row.invalid_rows
                    ),

                    "average_final_score": (
                        row.average_final_score
                    ),

                    "status": (
                        row.status
                    ),
                }
            )

        # -------------------------------------------------
        # Newest first
        # -------------------------------------------------

        history.sort(
            key=lambda item: item.get(
                "created_at",
                "",
            ),
            reverse=True,
        )

        return history


# =========================================================
# HISTORY DETAIL
# =========================================================

async def get_history_detail(
    history_id: str,
) -> dict | None:

    async with SessionLocal() as session:

        # -------------------------------------------------
        # Check single evaluation
        # -------------------------------------------------

        evaluation = await session.get(
            EvaluationRecord,
            history_id,
        )

        if evaluation:

            # Read directly from the same session
            # instead of opening another session.

            if evaluation.result_json:

                evaluation_result = (
                    EvaluationResult.model_validate(
                        json.loads(
                            evaluation.result_json
                        )
                    )
                )

            else:

                completeness_data = json.loads(
                    evaluation.completeness_analysis
                    or "{}"
                )

                hallucination_data = json.loads(
                    evaluation.hallucination_analysis
                    or "null"
                )

                evaluation_result = (
                    EvaluationResult(

                        id=evaluation.id,

                        question=evaluation.question,

                        response=evaluation.response,

                        scores=AgentScores(
                            **json.loads(
                                evaluation.scores
                            )
                        ),

                        explanations=(
                            AgentExplanations(
                                **json.loads(
                                    evaluation.explanations
                                    or "{}"
                                )
                            )
                        ),

                        completeness_analysis=(
                            CompletenessAnalysis(
                                **completeness_data
                            )
                        ),

                        hallucination_analysis=(
                            HallucinationAnalysis(
                                **hallucination_data
                            )
                            if hallucination_data
                            else None
                        ),

                        final_score=(
                            evaluation.final_score
                        ),

                        verdict=evaluation.verdict,
                    )
                )

            return {
                "id": history_id,

                "type": "single",

                "created_at": (
                    evaluation.created_at
                    or ""
                ),

                "evaluation": evaluation_result,

                "batch": None,
            }

        # -------------------------------------------------
        # Check batch evaluation
        # -------------------------------------------------

        batch = await session.get(
            BatchHistoryRecord,
            history_id,
        )

        if batch:

            batch_result = (
                BatchEvaluationResult.model_validate(
                    json.loads(
                        batch.batch_json
                    )
                )
            )

            return {
                "id": history_id,

                "type": "batch",

                "created_at": (
                    batch.created_at
                    or ""
                ),

                "evaluation": None,

                "batch": batch_result,
            }

        return None