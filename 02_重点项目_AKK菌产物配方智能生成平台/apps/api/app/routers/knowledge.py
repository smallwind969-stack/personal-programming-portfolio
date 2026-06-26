from fastapi import APIRouter, Query

from app.schemas.knowledge import KnowledgeChunk, KnowledgeItem
from app.services.knowledge_service import knowledge_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("", response_model=list[KnowledgeItem])
def list_knowledge(
    query: str | None = None,
    topic: list[str] = Query(default_factory=list),
) -> list[KnowledgeItem]:
    return knowledge_service.search_items(query=query, topics=topic)


@router.get("/chunks", response_model=list[KnowledgeChunk])
def list_knowledge_chunks(
    query: str | None = None,
    topic: list[str] = Query(default_factory=list),
    limit: int = Query(default=30, ge=1, le=100),
) -> list[KnowledgeChunk]:
    return knowledge_service.search_chunks(query=query, topics=topic, limit=limit)
