from pydantic import BaseModel


class KnowledgeItem(BaseModel):
    knowledgeId: str
    title: str
    sourceName: str
    sourceUrl: str
    sourceFile: str | None = None
    year: int | None = None
    evidenceType: str | None = None
    evidenceLevel: str
    topics: list[str]
    foodMatrix: list[str] = []
    akkMaterial: list[str] = []
    summary: str
    usableInsights: list[str]
    riskNotes: list[str]
    validationMetrics: list[str] = []
    retrievalScore: float | None = None
    matchReasons: list[str] = []
    keyPassages: list[str] = []


class KnowledgeChunk(BaseModel):
    chunkId: str
    knowledgeId: str
    title: str
    sourceName: str
    sourceFile: str | None = None
    sourceUrl: str
    evidenceLevel: str
    evidenceType: str | None = None
    topics: list[str] = []
    foodMatrix: list[str] = []
    text: str
    retrievalScore: float | None = None
    matchReasons: list[str] = []
