from fastapi import APIRouter

from app.schemas.llm import LlmStatus
from app.services.llm_service import local_llm_service

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/status", response_model=LlmStatus)
def get_llm_status() -> LlmStatus:
    return local_llm_service.status()
