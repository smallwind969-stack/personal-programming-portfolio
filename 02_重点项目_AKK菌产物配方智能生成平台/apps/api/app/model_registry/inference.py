from __future__ import annotations

import math

import numpy as np

from app.model_registry.contracts import PromotedModelPrediction
from app.model_registry.store import SqlitePromotedModelRegistry
from app.research.artifacts import ContentAddressedModelArtifactStore


class PromotedModelInferenceService:
    def __init__(self, registry: SqlitePromotedModelRegistry, artifacts: ContentAddressedModelArtifactStore) -> None:
        self.registry = registry
        self.artifacts = artifacts

    def predict(self, experiment_id: str, inputs: dict, model_version: str | None = None,
                allow_extrapolation: bool = False) -> PromotedModelPrediction:
        record = self.registry.get(experiment_id, model_version) if model_version else self.registry.latest(experiment_id)
        return self._predict_record(experiment_id, inputs, record, allow_extrapolation)

    def predict_target(
        self,
        experiment_id: str,
        target_field: str,
        inputs: dict,
        *,
        allow_extrapolation: bool = False,
    ) -> PromotedModelPrediction:
        record = self.registry.latest_by_target(experiment_id, target_field)
        return self._predict_record(experiment_id, inputs, record, allow_extrapolation)

    def _predict_record(self, experiment_id: str, inputs: dict, record,
                        allow_extrapolation: bool) -> PromotedModelPrediction:
        if (record is None or record.status != "approved"
                or record.validationStatus != "passed" or not record.active):
            raise LookupError("no approved model is registered for this experiment")
        missing = [name for name in record.featureNames if name not in inputs]
        if missing:
            raise ValueError(f"missing model features: {', '.join(missing)}")
        values: dict[str, float] = {}
        for name in record.featureNames:
            value = inputs[name]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError(f"model feature {name} must be a finite numeric value")
            values[name] = float(value)
        out_of_range = [name for name, value in values.items()
                        if name in record.featureRanges and not (record.featureRanges[name].min <= value <= record.featureRanges[name].max)]
        if out_of_range and not allow_extrapolation:
            raise ValueError(f"features outside training range: {', '.join(out_of_range)}")
        bundle = self.artifacts.load_verified(record.artifactFingerprint, record.artifactUri)
        if bundle.get("featureNames") != record.featureNames or bundle.get("targetField") != record.targetField:
            raise ValueError("model artifact contract does not match the approved registry record")
        prediction = float(bundle["model"].predict(np.asarray([[values[name] for name in record.featureNames]], dtype=float))[0])
        uncertainty_metric = record.uncertaintyMetric or ("rmse" if "rmse" in record.metrics else "mae")
        return PromotedModelPrediction(
            experimentId=experiment_id, modelVersion=record.modelVersion, trialId=record.trialId,
            datasetSnapshotId=record.datasetSnapshotId, datasetFingerprint=record.datasetFingerprint,
            artifactFingerprint=record.artifactFingerprint, targetField=record.targetField, prediction=prediction,
            extrapolated=bool(out_of_range), outOfRangeFeatures=out_of_range, featureValues=values,
            targetUnit=record.targetUnit, modelCategory=record.modelCategory,
            dataManifestUri=record.dataManifestUri, uncertainty=record.metrics.get(uncertainty_metric),
            featureRanges=record.featureRanges, metrics=record.metrics,
        )
