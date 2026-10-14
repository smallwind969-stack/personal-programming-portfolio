from __future__ import annotations

from app.model_registry.inference import PromotedModelInferenceService

from .contracts import DecisionPrediction, ModelLineage
from .errors import DecisionError


class ActivatedModelGateway:
    def __init__(self, inference: PromotedModelInferenceService) -> None:
        self.inference = inference

    def predict(
        self, experiment_id: str, target: str, features: dict[str, float]
    ) -> DecisionPrediction:
        try:
            result = self.inference.predict_target(
                experiment_id, target, features, allow_extrapolation=False
            )
        except LookupError as exc:
            raise DecisionError(
                "MODEL_NOT_AVAILABLE",
                f"目标 {target} 没有已激活模型。",
                details={"target": target},
            ) from exc
        except ValueError as exc:
            message = str(exc)
            if "outside training range" in message:
                code = "MODEL_INPUT_OUT_OF_RANGE"
            elif "missing model features" in message or "finite numeric" in message:
                code = "MODEL_FEATURE_MISMATCH"
            else:
                code = "MODEL_INFERENCE_FAILED"
            raise DecisionError(code, message, details={"target": target}) from exc

        return DecisionPrediction(
            targetField=result.targetField,
            value=result.prediction,
            uncertainty=result.uncertainty,
            lineage=ModelLineage(
                modelVersion=result.modelVersion,
                modelCategory=result.modelCategory,
                targetField=result.targetField,
                targetUnit=result.targetUnit,
                datasetSnapshotId=result.datasetSnapshotId,
                datasetFingerprint=result.datasetFingerprint,
                dataManifestUri=result.dataManifestUri,
                artifactFingerprint=result.artifactFingerprint,
                featureRanges={
                    name: bounds.model_dump() for name, bounds in result.featureRanges.items()
                },
                metrics=result.metrics,
            ),
        )

    def predict_many(
        self,
        experiment_id: str,
        inputs_by_target: dict[str, dict[str, float]],
    ) -> dict[str, DecisionPrediction]:
        return {
            target: self.predict(experiment_id, target, features)
            for target, features in inputs_by_target.items()
        }

    def common_feature_ranges(
        self, experiment_id: str, targets: list[str]
    ) -> dict[str, dict[str, float]]:
        records = []
        for target in targets:
            record = self.inference.registry.latest_by_target(experiment_id, target)
            if record is None:
                raise DecisionError(
                    "MODEL_NOT_AVAILABLE",
                    f"目标 {target} 没有已激活且验证通过的模型。",
                    details={"target": target},
                )
            records.append(record)
        names = set.intersection(*(set(record.featureNames) for record in records))
        ranges: dict[str, dict[str, float]] = {}
        for name in sorted(names):
            bounds = [record.featureRanges[name] for record in records]
            minimum = max(bound.min for bound in bounds)
            maximum = min(bound.max for bound in bounds)
            if minimum > maximum:
                raise DecisionError(
                    "NO_FEASIBLE_SOLUTION",
                    f"模型特征 {name} 的适用范围没有交集。",
                )
            ranges[name] = {"min": minimum, "max": maximum}
        if not ranges:
            raise DecisionError(
                "MODEL_FEATURE_MISMATCH", "所需目标模型不存在共同工艺特征。"
            )
        return ranges
