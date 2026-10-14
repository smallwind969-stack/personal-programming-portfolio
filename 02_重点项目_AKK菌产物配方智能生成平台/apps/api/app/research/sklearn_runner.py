from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version
import math
import platform
from time import monotonic
from typing import Any, Callable

import numpy as np
from sklearn.base import clone
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.research.artifacts import ContentAddressedModelArtifactStore
from app.research.runner import ResearchEvaluationContext, ResearchEvaluationOutcome


@dataclass
class NumericTrainingDataset:
    experimentId: str
    snapshotId: str
    datasetFingerprint: str
    featureNames: list[str]
    targetField: str
    X: np.ndarray
    y: np.ndarray
    holdoutStartIndex: int | None = None
    holdoutSource: str = "derived_ordered_fraction"


class SklearnResearchRunner:
    mode = "real_runner"
    runnerKey = "sklearn-time-series-modeling-v2"
    supportedAlgorithms = ("ridge", "random_forest", "gradient_boosting")

    def __init__(
        self,
        dataset_provider: Callable[[str, str], NumericTrainingDataset],
        artifact_store: ContentAddressedModelArtifactStore,
    ) -> None:
        self.datasetProvider = dataset_provider
        self.artifactStore = artifact_store

    def evaluate(
        self,
        baseline: dict[str, float],
        parameter_patch: dict,
        fixed_budget_seconds: int,
        context: ResearchEvaluationContext,
    ) -> ResearchEvaluationOutcome:
        del baseline, fixed_budget_seconds
        started = monotonic()
        try:
            dataset = self.datasetProvider(
                context.experimentId, context.datasetSnapshotId,
            )
            self._validate(dataset)
            algorithm, params = self._parameters(parameter_patch)
            estimator = self._estimator(algorithm, params)

            if dataset.holdoutStartIndex is not None:
                split = dataset.holdoutStartIndex
                holdout_rows = len(dataset.y) - split
            else:
                holdout_rows = max(2, int(math.ceil(len(dataset.y) * 0.2)))
                split = len(dataset.y) - holdout_rows
            train_x, train_y = dataset.X[:split], dataset.y[:split]
            holdout_x, holdout_y = dataset.X[split:], dataset.y[split:]
            if len(train_y) < 8:
                raise ValueError(
                    "real training requires at least 8 ordered training rows before holdout"
                )

            fold_count = min(5, max(2, len(train_y) // 8))
            splitter = TimeSeriesSplit(n_splits=fold_count)
            folds: list[dict[str, Any]] = []
            for fold_number, (train_index, validation_index) in enumerate(
                splitter.split(train_x), start=1,
            ):
                fold_model = clone(estimator)
                fold_model.fit(train_x[train_index], train_y[train_index])
                fold_prediction = fold_model.predict(train_x[validation_index])
                folds.append({
                    "fold": fold_number,
                    "trainStart": int(train_index[0]),
                    "trainEnd": int(train_index[-1]),
                    "validationStart": int(validation_index[0]),
                    "validationEnd": int(validation_index[-1]),
                    "trainRows": len(train_index),
                    "validationRows": len(validation_index),
                    "metrics": self._metrics(
                        train_y[validation_index], fold_prediction,
                    ),
                })

            estimator.fit(train_x, train_y)
            holdout_prediction = estimator.predict(holdout_x)
            metrics = self._metrics(holdout_y, holdout_prediction)
            cv_mean, cv_std = self._aggregate_folds(folds)
            residuals = holdout_y - holdout_prediction
            train_target_std = float(np.std(train_y))
            holdout_target_std = float(np.std(holdout_y))
            train_target_range = float(np.max(train_y) - np.min(train_y))
            holdout_target_range = float(np.max(holdout_y) - np.min(holdout_y))
            variance_ratio = holdout_target_std / max(train_target_std, 1e-12)
            low_variance_holdout = variance_ratio < 0.10
            holdout_diagnostics = {
                "trainTargetStd": round(train_target_std, 10),
                "holdoutTargetStd": round(holdout_target_std, 10),
                "varianceRatio": round(variance_ratio, 6),
                "trainTargetRange": round(train_target_range, 10),
                "holdoutTargetRange": round(holdout_target_range, 10),
                "normalizedMaeByTrainRange": round(float(metrics["mae"]) / max(train_target_range, 1e-12), 6),
                "r2Stable": not low_variance_holdout,
                "r2Interpretation": "unstable_low_variance_holdout" if low_variance_holdout else "standard",
            }
            feature_ranges = {
                name: {
                    "min": float(np.min(dataset.X[:, index])),
                    "max": float(np.max(dataset.X[:, index])),
                }
                for index, name in enumerate(dataset.featureNames)
            }
            train_feature_stats = self._feature_stats(train_x, dataset.featureNames)
            holdout_feature_stats = self._feature_stats(
                holdout_x, dataset.featureNames,
            )
            range_coverage = {
                name: round(float(np.mean(
                    (holdout_x[:, index] >= feature_ranges[name]["min"])
                    & (holdout_x[:, index] <= feature_ranges[name]["max"])
                )), 6)
                for index, name in enumerate(dataset.featureNames)
            }
            feature_effects = self._feature_effects(
                estimator, algorithm, dataset.featureNames,
            )
            residual_diagnostics = self._residual_diagnostics(
                residuals, holdout_prediction,
            )
            model_card = {
                "schemaVersion": "1.0",
                "algorithm": algorithm,
                "modelType": {
                    "ridge": "Ridge",
                    "random_forest": "RandomForestRegressor",
                    "gradient_boosting": "GradientBoostingRegressor",
                }[algorithm],
                "parameters": params,
                "randomState": 42,
                "datasetSnapshotId": dataset.snapshotId,
                "datasetFingerprint": dataset.datasetFingerprint,
                "featureNames": dataset.featureNames,
                "targetField": dataset.targetField,
                "splitStrategy": "ordered_holdout_with_expanding_window_cv",
                "shuffle": False,
                "trainRows": len(train_y),
                "holdoutRows": len(holdout_y),
                "holdoutSource": dataset.holdoutSource,
                "crossValidationFolds": folds,
                "crossValidationMean": cv_mean,
                "crossValidationStd": cv_std,
                "holdoutMetrics": metrics,
                "holdoutDiagnostics": holdout_diagnostics,
                "holdoutObservations": [
                    {
                        "rowIndex": split + index,
                        "actual": round(float(actual), 10),
                        "predicted": round(float(predicted), 10),
                        "residual": round(float(residual), 10),
                    }
                    for index, (actual, predicted, residual) in enumerate(
                        zip(holdout_y, holdout_prediction, residuals)
                    )
                ],
                "residualDiagnostics": residual_diagnostics,
                "featureRanges": feature_ranges,
                "trainFeatureStats": train_feature_stats,
                "holdoutFeatureStats": holdout_feature_stats,
                "holdoutRangeCoverage": range_coverage,
                "featureEffects": feature_effects,
                "targetRange": {
                    "min": float(np.min(train_y)),
                    "max": float(np.max(train_y)),
                    "std": float(np.std(train_y)),
                },
                "pythonVersion": platform.python_version(),
                "sklearnVersion": version("scikit-learn"),
                "limitations": [
                    "模型仅适用于已确认特征范围内的研发预测。",
                    "验证结果来自历史时间顺序切分，不等同于实际产线安全认证。",
                    "外推输入必须被仿真层标记并由研发人员复核。",
                ],
            }
            if low_variance_holdout:
                model_card["limitations"].append(
                    "留出集目标方差过低，R² 对微小误差高度敏感；应同时参考归一化 MAE，并补充多批次数据。"
                )
            metadata = {
                "runnerKey": self.runnerKey,
                "experimentId": context.experimentId,
                "campaignId": context.campaignId,
                "trialSequence": context.trialSequence,
                **model_card,
            }
            stored = self.artifactStore.save(
                {
                    "model": estimator,
                    "featureNames": dataset.featureNames,
                    "targetField": dataset.targetField,
                },
                metadata,
            )
            return ResearchEvaluationOutcome(
                metrics=metrics,
                durationSeconds=monotonic() - started,
                artifactFingerprint=stored.fingerprint,
                artifactUri=stored.uri,
                datasetFingerprint=dataset.datasetFingerprint,
                featureNames=dataset.featureNames,
                targetField=dataset.targetField,
                modelType=model_card["modelType"],
                featureRanges=feature_ranges,
                modelCard=model_card,
            )
        except Exception as exc:
            return ResearchEvaluationOutcome(
                {"mae": 0.0, "rmse": 0.0, "r2": 0.0},
                monotonic() - started,
                str(exc),
            )

    @staticmethod
    def _validate(dataset: NumericTrainingDataset) -> None:
        if len(dataset.y) < 12:
            raise ValueError("real training requires at least 12 complete numeric rows")
        if (
            dataset.X.ndim != 2
            or dataset.X.shape[0] != len(dataset.y)
            or dataset.X.shape[1] < 1
        ):
            raise ValueError("training matrix shape is invalid")
        if not np.isfinite(dataset.X).all() or not np.isfinite(dataset.y).all():
            raise ValueError("training matrix contains non-finite values")
        if len(dataset.featureNames) != dataset.X.shape[1]:
            raise ValueError("feature contract does not match matrix")
        if len(dataset.featureNames) != len(set(dataset.featureNames)):
            raise ValueError("feature names must be unique")

    @classmethod
    def _parameters(cls, patch: dict) -> tuple[str, dict[str, Any]]:
        algorithm = str(patch.get("algorithm", "gradient_boosting"))
        if algorithm not in cls.supportedAlgorithms:
            raise ValueError(
                "unsupported modeling algorithm: "
                + algorithm
                + "; choose "
                + ", ".join(cls.supportedAlgorithms)
            )
        if algorithm == "ridge":
            return algorithm, {
                "alpha": max(0.0001, min(1000.0, float(patch.get("alpha", 1.0)))),
            }
        if algorithm == "random_forest":
            return algorithm, {
                "n_estimators": max(20, min(500, int(patch.get("nEstimators", 160)))),
                "max_depth": (
                    None
                    if patch.get("maxDepth") is None
                    else max(1, min(30, int(patch["maxDepth"])))
                ),
                "min_samples_leaf": max(
                    1, min(50, int(patch.get("minSamplesLeaf", 1)))
                ),
            }
        return algorithm, {
            "n_estimators": max(10, min(500, int(patch.get("nEstimators", 100)))),
            "learning_rate": max(
                0.005, min(0.5, float(patch.get("learningRate", 0.05)))
            ),
            "max_depth": max(1, min(12, int(patch.get("maxDepth", 3)))),
            "min_samples_leaf": max(
                1, min(50, int(patch.get("minSamplesLeaf", 1)))
            ),
            "subsample": max(0.5, min(1.0, float(patch.get("subsample", 1.0)))),
        }

    @staticmethod
    def _estimator(algorithm: str, params: dict[str, Any]):
        if algorithm == "ridge":
            return make_pipeline(StandardScaler(), Ridge(**params))
        if algorithm == "random_forest":
            return RandomForestRegressor(random_state=42, n_jobs=1, **params)
        return GradientBoostingRegressor(random_state=42, **params)

    @staticmethod
    def _metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
        r2 = float(r2_score(actual, predicted)) if len(actual) >= 2 else 0.0
        if not math.isfinite(r2):
            r2 = 0.0
        return {
            "mae": round(float(mean_absolute_error(actual, predicted)), 6),
            "rmse": round(float(mean_squared_error(actual, predicted) ** 0.5), 6),
            "r2": round(r2, 6),
        }

    @staticmethod
    def _aggregate_folds(
        folds: list[dict[str, Any]],
    ) -> tuple[dict[str, float], dict[str, float]]:
        means: dict[str, float] = {}
        deviations: dict[str, float] = {}
        for metric in ("mae", "rmse", "r2"):
            values = np.asarray(
                [fold["metrics"][metric] for fold in folds], dtype=float,
            )
            means[metric] = round(float(np.mean(values)), 6)
            deviations[metric] = round(float(np.std(values)), 6)
        return means, deviations

    @staticmethod
    def _feature_stats(
        values: np.ndarray, names: list[str],
    ) -> dict[str, dict[str, float]]:
        return {
            name: {
                "mean": round(float(np.mean(values[:, index])), 10),
                "std": round(float(np.std(values[:, index])), 10),
                "min": round(float(np.min(values[:, index])), 10),
                "max": round(float(np.max(values[:, index])), 10),
            }
            for index, name in enumerate(names)
        }

    @staticmethod
    def _feature_effects(estimator, algorithm: str, names: list[str]) -> list[dict]:
        if algorithm == "ridge":
            coefficients = np.asarray(estimator[-1].coef_, dtype=float)
            method = "standardized_coefficient"
            values = coefficients
        else:
            values = np.asarray(estimator.feature_importances_, dtype=float)
            method = "impurity_importance"
        magnitude = float(np.sum(np.abs(values))) or 1.0
        return [
            {
                "feature": name,
                "effect": round(float(value), 10),
                "normalizedImportance": round(float(abs(value) / magnitude), 10),
                "method": method,
            }
            for name, value in zip(names, values)
        ]

    @staticmethod
    def _residual_diagnostics(
        residuals: np.ndarray, predictions: np.ndarray,
    ) -> dict[str, float]:
        residual_std = float(np.std(residuals))
        if len(residuals) >= 3 and residual_std > 0:
            autocorrelation = float(np.corrcoef(residuals[:-1], residuals[1:])[0, 1])
            prediction_correlation = (
                float(np.corrcoef(predictions, residuals)[0, 1])
                if float(np.std(predictions)) > 0 else 0.0
            )
        else:
            autocorrelation = 0.0
            prediction_correlation = 0.0
        if not math.isfinite(autocorrelation):
            autocorrelation = 0.0
        if not math.isfinite(prediction_correlation):
            prediction_correlation = 0.0
        return {
            "meanResidual": round(float(np.mean(residuals)), 10),
            "residualStd": round(residual_std, 10),
            "meanAbsoluteResidual": round(float(np.mean(np.abs(residuals))), 10),
            "maxAbsoluteResidual": round(float(np.max(np.abs(residuals))), 10),
            "lag1Autocorrelation": round(autocorrelation, 10),
            "predictionResidualCorrelation": round(prediction_correlation, 10),
        }
