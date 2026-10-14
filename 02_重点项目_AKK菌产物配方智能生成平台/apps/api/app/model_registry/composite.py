from __future__ import annotations

from typing import Literal

from typing import Any

from pydantic import BaseModel, Field

from app.model_registry.bindings import FeatureBindingAudit, SimulationFeatureBindingService
from app.model_registry.inference import PromotedModelInferenceService
from app.model_registry.store import SqlitePromotedModelRegistry


class ApproximatePredictionInterval(BaseModel):
    lower: float
    upper: float
    method: Literal["approximate95_rmse", "empirical_holdout_absolute_error"] = "approximate95_rmse"
    coverageClaim: Literal["not_calibrated", "empirical_holdout"] = "not_calibrated"


class CompositeTargetPrediction(BaseModel):
    targetField: str
    prediction: float
    interval: ApproximatePredictionInterval
    modelVersion: str
    trialId: str
    bindingVersion: str
    datasetSnapshotId: str
    datasetFingerprint: str
    artifactFingerprint: str
    extrapolated: bool
    outOfRangeFeatures: list[str]
    bindingAudit: list[FeatureBindingAudit]
    metrics: dict[str, float]


class CompositeModelPrediction(BaseModel):
    experimentId: str
    predictionSource: Literal["promoted_model_composite"] = "promoted_model_composite"
    reliability: Literal["low", "medium", "high"]
    targets: list[CompositeTargetPrediction]
    unavailableTargets: list[str]
    unavailableReasons: dict[str, str]
    disclaimer: str = "研发实验建议；近似区间未经统计校准，不能替代小试、中试和人工审核。"


class CompositePredictionRequest(BaseModel):
    parameters: dict[str, Any] = Field(min_length=1)
    targetFields: list[str] = Field(min_length=1)
    allowExtrapolation: bool = False


class CompositeModelPredictionService:
    def __init__(self, registry: SqlitePromotedModelRegistry, bindings: SimulationFeatureBindingService,
                 inference: PromotedModelInferenceService) -> None:
        self.registry = registry
        self.bindings = bindings
        self.inference = inference

    def predict(self, experiment_id: str, parameters: dict, target_fields: list[str] | None = None,
                allow_extrapolation: bool = False) -> CompositeModelPrediction:
        requested = target_fields or [record.targetField for record in self.registry.latest_per_target(experiment_id)]
        targets: list[CompositeTargetPrediction] = []
        unavailable: list[str] = []; reasons: dict[str, str] = {}
        for target_field in requested:
            record = self.registry.latest_by_target(experiment_id, target_field)
            if record is None:
                unavailable.append(target_field); reasons[target_field] = "no approved model"
                continue
            try:
                bound = self.bindings.bind(experiment_id, record.modelVersion, parameters)
            except LookupError as exc:
                unavailable.append(target_field); reasons[target_field] = str(exc)
                continue
            prediction = self.inference.predict(
                experiment_id, bound.modelInputs, record.modelVersion, allow_extrapolation,
            )
            rmse = max(0.0, float(record.metrics.get("rmse", 0.0)))
            margin = 1.96 * rmse
            targets.append(CompositeTargetPrediction(
                targetField=target_field, prediction=prediction.prediction,
                interval=ApproximatePredictionInterval(lower=prediction.prediction - margin,
                                                       upper=prediction.prediction + margin),
                modelVersion=record.modelVersion, trialId=record.trialId, bindingVersion=bound.bindingVersion,
                datasetSnapshotId=record.datasetSnapshotId, datasetFingerprint=record.datasetFingerprint,
                artifactFingerprint=record.artifactFingerprint, extrapolated=prediction.extrapolated,
                outOfRangeFeatures=prediction.outOfRangeFeatures, bindingAudit=bound.audit, metrics=record.metrics,
            ))
        r2_values = [item.metrics.get("r2", -1.0) for item in targets]
        if targets and not any(item.extrapolated for item in targets) and min(r2_values) >= 0.8:
            reliability = "high"
        elif targets and not any(item.extrapolated for item in targets) and min(r2_values) >= 0.5:
            reliability = "medium"
        else:
            reliability = "low"
        return CompositeModelPrediction(experimentId=experiment_id, reliability=reliability, targets=targets,
                                        unavailableTargets=unavailable, unavailableReasons=reasons)
