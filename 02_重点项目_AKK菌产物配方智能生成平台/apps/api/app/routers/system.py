from fastapi import APIRouter

from app.repositories.mock_repository import MockRepository
from app.services.llm_service import local_llm_service

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
def system_status() -> dict:
    repository = MockRepository()
    products = repository.get_products()
    knowledge_items = repository.get_knowledge_items()
    knowledge_chunks = repository.get_knowledge_chunks()
    return {
        "status": "ok",
        "productCount": len(products),
        "knowledgeItemCount": len(knowledge_items),
        "knowledgeChunkCount": len(knowledge_chunks),
        "llm": local_llm_service.status().model_dump(),
        "researchUseOnly": True,
    }
