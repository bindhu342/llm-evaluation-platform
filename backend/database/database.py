import os
import json
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy import String, Float, Text
from sqlalchemy.ext.asyncio import async_sessionmaker
from backend.models.schemas import EvaluationResult, AgentScores, AgentExplanations

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/evaluations.db")

engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class EvaluationRecord(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)
    scores: Mapped[str] = mapped_column(Text)         # JSON
    explanations: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    final_score: Mapped[float] = mapped_column(Float)
    verdict: Mapped[str] = mapped_column(String)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def save_result(result: EvaluationResult) -> None:
    async with SessionLocal() as session:
        record = EvaluationRecord(
            id=result.id,
            question=result.question,
            response=result.response,
            scores=result.scores.model_dump_json(),
            explanations=result.explanations.model_dump_json(),
            final_score=result.final_score,
            verdict=result.verdict,
        )
        session.add(record)
        await session.commit()


async def get_result(evaluation_id: str) -> EvaluationResult | None:
    async with SessionLocal() as session:
        row = await session.get(EvaluationRecord, evaluation_id)
        if not row:
            return None
        return EvaluationResult(
            id=row.id,
            question=row.question,
            response=row.response,
            scores=AgentScores(**json.loads(row.scores)),
            explanations=AgentExplanations(**json.loads(row.explanations or "{}")),
            final_score=row.final_score,
            verdict=row.verdict,
        )
