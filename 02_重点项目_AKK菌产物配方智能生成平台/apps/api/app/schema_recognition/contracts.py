from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


SchemaDataType = Literal["number", "string", "datetime", "boolean"]


class SchemaFieldContext(BaseModel):
    originalColumn: str
    sampleValues: list[str] = Field(max_length=5)


class SchemaAssetContext(BaseModel):
    assetId: str
    originalName: str
    detectedFormat: str
    fields: list[SchemaFieldContext]


class SchemaRecognitionContext(BaseModel):
    experimentId: str
    assets: list[SchemaAssetContext]


class ProviderCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assetId: str | None = None
    originalColumn: str
    standardField: str
    dataType: SchemaDataType
    sourceUnit: str | None = None
    targetUnit: str | None = None
    isTimeField: bool
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(min_length=1, max_length=5)


class SchemaProviderFailure(RuntimeError):
    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


class SchemaRecognitionProvider(Protocol):
    provider: str
    model: str

    def recognize(self, context: SchemaRecognitionContext) -> list[ProviderCandidate]: ...
