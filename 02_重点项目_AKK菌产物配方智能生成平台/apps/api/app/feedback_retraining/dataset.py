from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from typing import Callable

import numpy as np

from app.feedback_retraining.contracts import FeedbackDerivedDataset
from app.research.sklearn_runner import NumericTrainingDataset
from app.services.experiment_data_store import SqliteExperimentDataStore


class FeedbackRetrainingDatasetConflictError(RuntimeError):
    pass


class FeedbackRetrainingDatasetNotFoundError(LookupError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


_FEATURE_ALIASES = {
    "temperaturec": "temperatureC",
    "temperature": "temperatureC",
    "tempc": "temperatureC",
    "ph": "ph",
    "agitationrpm": "stirringRpm",
    "stirringrpm": "stirringRpm",
    "culturehours": "cultureHours",
}


def _content_payload(dataset: FeedbackDerivedDataset | dict) -> dict:
    payload = (
        dataset.model_dump(mode="json")
        if isinstance(dataset, FeedbackDerivedDataset)
        else dict(dataset)
    )
    return {
        key: value for key, value in payload.items()
        if key not in {"datasetId", "datasetFingerprint", "createdAt"}
    }


def _fingerprint(payload: dict) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


class FeedbackDerivedDatasetBuilder:
    def __init__(
        self,
        store: SqliteExperimentDataStore,
        base_dataset_provider: Callable[[str, str], NumericTrainingDataset],
        registry,
    ) -> None:
        self.store = store
        self.baseDatasetProvider = base_dataset_provider
        self.registry = registry

    def build(
        self,
        experiment_id: str,
        parent_model_version: str,
        feedback_dataset_versions: list[str],
    ) -> FeedbackDerivedDataset:
        versions = list(dict.fromkeys(feedback_dataset_versions))
        if not versions or len(versions) != len(feedback_dataset_versions):
            raise FeedbackRetrainingDatasetConflictError(
                "at least one unique feedback dataset version is required"
            )
        parent = self.registry.get(experiment_id, parent_model_version)
        if parent is None:
            raise FeedbackRetrainingDatasetConflictError(
                "parent promoted model was not found"
            )
        base = self.baseDatasetProvider(experiment_id, parent.datasetSnapshotId)
        if (
            base.datasetFingerprint != parent.datasetFingerprint
            or base.featureNames != list(parent.featureNames)
            or _normalized(base.targetField) != _normalized(parent.targetField)
        ):
            raise FeedbackRetrainingDatasetConflictError(
                "parent training dataset contract does not match promoted model lineage"
            )

        rows = [
            {
                **{
                    name: float(base.X[index, position])
                    for position, name in enumerate(base.featureNames)
                },
                base.targetField: float(base.y[index]),
            }
            for index in range(len(base.y))
        ]
        feedback_rows: list[dict[str, float]] = []
        for version in versions:
            payload = self.store.get("experimental_feedback_dataset", version)
            if payload is None or payload.get("experimentId") != experiment_id:
                raise FeedbackRetrainingDatasetConflictError(
                    f"feedback dataset {version} was not found"
                )
            if payload.get("parentModelVersion") != parent_model_version:
                raise FeedbackRetrainingDatasetConflictError(
                    "feedback dataset parent model does not match retraining parent"
                )
            source_type = payload.get("sourceType", "optimization_validation")
            if source_type == "optimization_validation":
                batch_kind = "experimental_validation_batch"
                batch_id = payload.get("validationBatchId", "")
            elif source_type == "supplementary_measurement":
                batch_kind = "supplementary_measurement_batch"
                batch_id = payload.get("supplementaryMeasurementBatchId", "")
            else:
                raise FeedbackRetrainingDatasetConflictError(
                    f"feedback dataset {version} has an unsupported source type"
                )
            batch = self.store.get(batch_kind, batch_id)
            gate = (batch or {}).get("qualityGate") or {}
            if (
                not batch
                or batch.get("status") != "confirmed"
                or not gate.get("eligible")
                or gate.get("feedbackDatasetVersion") != version
            ):
                raise FeedbackRetrainingDatasetConflictError(
                    f"feedback dataset {version} is not confirmed and eligible"
                )
            for raw_row in payload.get("rows", []):
                feedback_rows.append(
                    self._project_row(raw_row, base.featureNames, base.targetField)
                )
        if not feedback_rows:
            raise FeedbackRetrainingDatasetConflictError(
                "feedback datasets contain no usable rows"
            )

        external_holdout_count = min(3, len(feedback_rows))
        training_feedback_count = len(feedback_rows) - external_holdout_count
        holdout_start_index = len(rows) + training_feedback_count

        content = {
            "experimentId": experiment_id,
            "parentModelVersion": parent_model_version,
            "parentDatasetSnapshotId": parent.datasetSnapshotId,
            "parentDatasetFingerprint": parent.datasetFingerprint,
            "feedbackDatasetVersions": versions,
            "featureNames": list(base.featureNames),
            "targetField": base.targetField,
            "historicalRowCount": len(rows),
            "feedbackRowCount": len(feedback_rows),
            "trainingFeedbackRowCount": training_feedback_count,
            "externalHoldoutRowCount": external_holdout_count,
            "holdoutStartIndex": holdout_start_index,
            "totalRowCount": len(rows) + len(feedback_rows),
            "rows": rows + feedback_rows,
        }
        fingerprint = _fingerprint(content)
        existing = next(
            (
                FeedbackDerivedDataset.model_validate(item)
                for item in self.store.list(
                    "feedback_derived_dataset", experiment_id
                )
                if item.get("datasetFingerprint") == fingerprint
            ),
            None,
        )
        if existing is not None:
            return existing
        dataset = FeedbackDerivedDataset(
            datasetId="feedback-derived-dataset-" + fingerprint[-12:],
            datasetFingerprint=fingerprint,
            createdAt=_now(),
            **content,
        )
        self.store.save(
            "feedback_derived_dataset", dataset.datasetId,
            experiment_id, dataset.model_dump(mode="json"),
        )
        return dataset.model_copy(deep=True)

    def get(self, experiment_id: str, dataset_id: str) -> FeedbackDerivedDataset:
        payload = self.store.get("feedback_derived_dataset", dataset_id)
        if payload is None or payload.get("experimentId") != experiment_id:
            raise FeedbackRetrainingDatasetNotFoundError(dataset_id)
        dataset = FeedbackDerivedDataset.model_validate(payload)
        if _fingerprint(_content_payload(dataset)) != dataset.datasetFingerprint:
            raise FeedbackRetrainingDatasetConflictError(
                "derived feedback dataset fingerprint verification failed"
            )
        return dataset

    def load_numeric(
        self, experiment_id: str, dataset_id: str,
    ) -> NumericTrainingDataset:
        dataset = self.get(experiment_id, dataset_id)
        return NumericTrainingDataset(
            experimentId=experiment_id,
            snapshotId=dataset.datasetId,
            datasetFingerprint=dataset.datasetFingerprint,
            featureNames=list(dataset.featureNames),
            targetField=dataset.targetField,
            X=np.asarray([
                [float(row[name]) for name in dataset.featureNames]
                for row in dataset.rows
            ], dtype=float),
            y=np.asarray([
                float(row[dataset.targetField]) for row in dataset.rows
            ], dtype=float),
            holdoutStartIndex=dataset.holdoutStartIndex,
            holdoutSource="confirmed_feedback_batches",
        )

    @staticmethod
    def _project_row(
        row: dict,
        feature_names: list[str],
        target_field: str,
    ) -> dict[str, float]:
        normalized_keys = {_normalized(key): key for key in row}

        def value_for(field: str, *, target: bool = False) -> float:
            normalized_field = _normalized(field)
            source = normalized_keys.get(normalized_field)
            if source is None and not target:
                alias = _FEATURE_ALIASES.get(normalized_field)
                if alias is not None:
                    source = normalized_keys.get(_normalized(alias))
            value = row.get(source) if source is not None else None
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                kind = "target" if target else "feature"
                raise FeedbackRetrainingDatasetConflictError(
                    f"feedback {kind} {field} is missing or non-numeric"
                )
            return float(value)

        return {
            **{name: value_for(name) for name in feature_names},
            target_field: value_for(target_field, target=True),
        }


def load_persisted_feedback_numeric_dataset(
    store: SqliteExperimentDataStore,
    experiment_id: str,
    dataset_id: str,
) -> NumericTrainingDataset:
    payload = store.get("feedback_derived_dataset", dataset_id)
    if payload is None or payload.get("experimentId") != experiment_id:
        raise FeedbackRetrainingDatasetNotFoundError(dataset_id)
    dataset = FeedbackDerivedDataset.model_validate(payload)
    if _fingerprint(_content_payload(dataset)) != dataset.datasetFingerprint:
        raise FeedbackRetrainingDatasetConflictError(
            "derived feedback dataset fingerprint verification failed"
        )
    return NumericTrainingDataset(
        experimentId=experiment_id,
        snapshotId=dataset.datasetId,
        datasetFingerprint=dataset.datasetFingerprint,
        featureNames=list(dataset.featureNames),
        targetField=dataset.targetField,
        X=np.asarray([
            [float(row[name]) for name in dataset.featureNames]
            for row in dataset.rows
        ], dtype=float),
        y=np.asarray([
            float(row[dataset.targetField]) for row in dataset.rows
        ], dtype=float),
        holdoutStartIndex=dataset.holdoutStartIndex,
        holdoutSource="confirmed_feedback_batches",
    )
