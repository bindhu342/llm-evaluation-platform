from fastapi import APIRouter, HTTPException
from backend.models.schemas import EvaluationRequest, EvaluationResult
from backend.evaluation.orchestrator import Orchestrator
from backend.database.database import save_result, get_result

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation"])

# Instantiated lazily so a missing .env does not crash the server on startup.
# The 503 response clearly reports the configuration problem to the caller.
_orchestrator: Orchestrator | None = None


def _get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


@router.post("/submit", response_model=EvaluationResult)
async def submit_evaluation(request: EvaluationRequest):
    try:
        result = await _get_orchestrator().run(request)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Evaluation failed: {str(e)}")

    await save_result(result)
    return result


@router.get("/result/{evaluation_id}", response_model=EvaluationResult)
async def get_evaluation(evaluation_id: str):
    result = await get_result(evaluation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return result
