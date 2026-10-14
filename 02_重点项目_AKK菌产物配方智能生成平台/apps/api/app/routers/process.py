from fastapi import APIRouter

from app.schemas.process import (
    ExperimentFeedback,
    ExperimentFeedbackRequest,
    GeneratedProcessTask,
    ProcessTaskRequest,
    ProductionLineProfile,
)
from app.services.process_service import create_feedback, generate_process_task, list_production_lines

router = APIRouter(prefix="/process", tags=["process"])


@router.get("/production-lines", response_model=list[ProductionLineProfile])
def get_production_lines() -> list[ProductionLineProfile]:
    return list_production_lines()


@router.post("/tasks/generate", response_model=GeneratedProcessTask)
def generate_task(payload: ProcessTaskRequest) -> GeneratedProcessTask:
    return generate_process_task(payload)


@router.post("/feedback", response_model=ExperimentFeedback)
def submit_feedback(payload: ExperimentFeedbackRequest) -> ExperimentFeedback:
    return create_feedback(payload)
