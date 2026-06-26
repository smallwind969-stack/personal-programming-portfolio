from fastapi import APIRouter

from app.schemas.experiments import ExperimentRecord
from app.services.experiment_service import experiment_service

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("", response_model=list[ExperimentRecord])
def list_experiments(result_id: str | None = None) -> list[ExperimentRecord]:
    return experiment_service.list_records(result_id)
