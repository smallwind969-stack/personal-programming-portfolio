from __future__ import annotations

from pydantic import BaseModel, Field

from app.model_registry.bindings import FeatureBindingVersion
from app.model_registry.contracts import PromotedModelRecord
from app.enterprise_knowledge.usage import EnterpriseKnowledgeUsage


class ModelAssetEvaluation(BaseModel):
    reportId: str
    status: str
    reliabilityScore: float = Field(ge=0, le=1)
    reliabilityGrade: str
    recommendedAdmission: bool
    admissionAllowed: bool
    artifactVerified: bool


class ModelSimulationUsage(BaseModel):
    runId: str
    version: int
    status: str
    bindingVersions: list[str]
    reliabilityScore: float | None = Field(default=None, ge=0, le=1)
    officialSnapshotId: str | None = None
    updatedAt: str


class ModelAssetSummary(BaseModel):
    experimentId: str
    experimentName: str
    modelVersion: str
    targetField: str
    modelType: str
    approvedAt: str
    approvedBy: str
    status: str
    latest: bool
    datasetSnapshotId: str
    featureCount: int = Field(ge=1)
    metrics: dict[str, float]
    artifactVerified: bool
    evaluationStatus: str | None = None
    reliabilityScore: float | None = Field(default=None, ge=0, le=1)
    bindingVersion: str | None = None
    simulationUsageCount: int = Field(ge=0)


class ModelAssetDetail(BaseModel):
    experimentName: str
    latest: bool
    artifactVerified: bool
    record: PromotedModelRecord
    evaluationReport: ModelAssetEvaluation | None = None
    binding: FeatureBindingVersion | None = None
    simulationUsages: list[ModelSimulationUsage]
    knowledgeUsages: list[EnterpriseKnowledgeUsage] = Field(default_factory=list)
    disclaimer: str = "模型资产详情为只读证据投影；模型晋升、绑定确认和仿真准入仍需在原业务工作台完成人工门禁。"
