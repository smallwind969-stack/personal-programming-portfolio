from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


RequirementDirection = Literal["maximize", "minimize", "target", "range"]


class RequirementAttribute(BaseModel):
    """A measurable product or process requirement extracted from user input."""

    metric: str = Field(min_length=1)
    direction: RequirementDirection
    threshold: float | None = None
    upperThreshold: float | None = None
    unit: str | None = None
    measurementMethod: str | None = None
    sourceText: str | None = None


class DecisionRequirement(BaseModel):
    """Structured requirement without silently inventing missing constraints."""

    productType: str = Field(min_length=1)
    attributes: list[RequirementAttribute] = Field(default_factory=list)
    missingConstraints: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)


class EvidenceSource(BaseModel):
    title: str = Field(min_length=1)
    url: str | None = None
    file: str | None = None
    location: str | None = None


class KnowledgeEvidence(BaseModel):
    evidenceId: str = Field(min_length=1)
    productTypes: list[str] = Field(default_factory=list)
    organisms: list[str] = Field(default_factory=list)
    ingredients: dict[str, list[float]] = Field(default_factory=dict)
    processRanges: dict[str, list[float]] = Field(default_factory=dict)
    metrics: list[str] = Field(default_factory=list)
    disabledConditions: list[str] = Field(default_factory=list)
    source: EvidenceSource
    evidenceKind: Literal[
        "author_table",
        "author_supplement",
        "figure_digitized",
        "peer_reviewed_article",
        "internal_record",
    ]
    evidenceLevel: Literal[
        "peer_reviewed_direct",
        "public_dataset_direct",
        "internal_verified",
        "internal_unverified",
    ]
    contentFingerprint: str = Field(pattern=r"^sha256:[0-9a-fA-F]{8,64}$")
    version: str = Field(min_length=1)
    status: Literal["active", "draft", "disabled"]


class ModelLineage(BaseModel):
    modelVersion: str
    modelCategory: str
    targetField: str
    targetUnit: str | None = None
    datasetSnapshotId: str
    datasetFingerprint: str
    dataManifestUri: str | None = None
    artifactFingerprint: str
    featureRanges: dict[str, dict[str, float]]
    metrics: dict[str, float]


class DecisionPrediction(BaseModel):
    targetField: str
    value: float
    uncertainty: float | None = None
    lineage: ModelLineage


class DecisionFailure(BaseModel):
    """Stable, machine-readable failure returned by the decision workflow."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)
