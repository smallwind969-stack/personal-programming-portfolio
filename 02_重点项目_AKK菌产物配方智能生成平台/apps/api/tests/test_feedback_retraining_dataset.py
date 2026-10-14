from types import SimpleNamespace

import numpy as np
import pytest

from app.feedback_retraining.dataset import (
    FeedbackDerivedDatasetBuilder,
    FeedbackRetrainingDatasetConflictError,
)
from app.research.sklearn_runner import NumericTrainingDataset
from app.services.experiment_data_store import SqliteExperimentDataStore


def _base_dataset(experiment_id: str, snapshot_id: str) -> NumericTrainingDataset:
    assert experiment_id == "exp-1"
    assert snapshot_id == "dataset-parent-v1"
    return NumericTrainingDataset(
        experimentId=experiment_id,
        snapshotId=snapshot_id,
        datasetFingerprint="sha256:parent-data",
        featureNames=["temperature_c", "ph", "agitation_rpm"],
        targetField="od600",
        X=np.asarray([
            [36.0 + index * 0.1, 6.7 + index * 0.01, 180 + index]
            for index in range(12)
        ], dtype=float),
        y=np.asarray([1.5 + index * 0.1 for index in range(12)], dtype=float),
    )


@pytest.fixture()
def builder(tmp_path):
    store = SqliteExperimentDataStore(tmp_path / "feedback.db", tmp_path / "objects")
    registry = SimpleNamespace(get=lambda experiment_id, model_version: SimpleNamespace(
        experimentId=experiment_id,
        modelVersion=model_version,
        datasetSnapshotId="dataset-parent-v1",
        datasetFingerprint="sha256:parent-data",
        featureNames=["temperature_c", "ph", "agitation_rpm"],
        targetField="od600",
    ))
    store.save("experimental_validation_batch", "batch-1", "exp-1", {
        "validationBatchId": "batch-1",
        "experimentId": "exp-1",
        "status": "confirmed",
        "qualityGate": {"eligible": True, "feedbackDatasetVersion": "feedback-v1"},
    })
    store.save("experimental_feedback_dataset", "feedback-v1", "exp-1", {
        "feedbackDatasetVersion": "feedback-v1",
        "experimentId": "exp-1",
        "validationBatchId": "batch-1",
        "parentModelVersion": "model-v1",
        "parameterVersion": "process-v1",
        "rows": [{
            "temperatureC": 38.0,
            "ph": 6.9,
            "cultureHours": 48.0,
            "stirringRpm": 202.0,
            "OD600": 2.93,
            "replicateCount": 3,
            "batchCode": "LAB-001",
        }],
        "measurementIds": ["m1", "m2", "m3"],
        "createdAt": "2026-07-21T01:00:00+00:00",
    })
    return FeedbackDerivedDatasetBuilder(store, _base_dataset, registry), store


def test_builder_appends_confirmed_feedback_using_parent_feature_contract(builder):
    service, _store = builder

    derived = service.build("exp-1", "model-v1", ["feedback-v1"])

    assert derived.parentDatasetSnapshotId == "dataset-parent-v1"
    assert derived.featureNames == ["temperature_c", "ph", "agitation_rpm"]
    assert derived.targetField == "od600"
    assert derived.historicalRowCount == 12
    assert derived.feedbackRowCount == 1
    assert derived.totalRowCount == 13
    assert derived.trainingFeedbackRowCount == 0
    assert derived.externalHoldoutRowCount == 1
    assert derived.holdoutStartIndex == 12
    assert derived.rows[-1] == {
        "temperature_c": 38.0,
        "ph": 6.9,
        "agitation_rpm": 202.0,
        "od600": 2.93,
    }
    numeric = service.load_numeric("exp-1", derived.datasetId)
    assert numeric.X.shape == (13, 3)
    assert numeric.y[-1] == pytest.approx(2.93)
    assert numeric.datasetFingerprint == derived.datasetFingerprint
    assert numeric.holdoutStartIndex == 12
    assert numeric.holdoutSource == "confirmed_feedback_batches"


def test_builder_is_idempotent_and_recovers_persisted_dataset(builder):
    service, store = builder
    first = service.build("exp-1", "model-v1", ["feedback-v1"])
    second = service.build("exp-1", "model-v1", ["feedback-v1"])
    recovered = FeedbackDerivedDatasetBuilder(store, _base_dataset, service.registry)

    assert second.datasetId == first.datasetId
    assert recovered.get("exp-1", first.datasetId).datasetFingerprint == first.datasetFingerprint
    assert recovered.load_numeric("exp-1", first.datasetId).X.tolist() == service.load_numeric("exp-1", first.datasetId).X.tolist()


def test_builder_rejects_feedback_without_confirmed_quality_gate(builder):
    service, store = builder
    payload = store.get("experimental_validation_batch", "batch-1")
    payload["qualityGate"]["eligible"] = False
    store.save("experimental_validation_batch", "batch-1", "exp-1", payload)

    with pytest.raises(FeedbackRetrainingDatasetConflictError, match="eligible"):
        service.build("exp-1", "model-v1", ["feedback-v1"])


def test_builder_rejects_feedback_target_that_does_not_match_parent_model(builder):
    service, store = builder
    payload = store.get("experimental_feedback_dataset", "feedback-v1")
    payload["rows"][0]["OD600"] = None
    payload["rows"][0]["yield"] = 9.2
    store.save("experimental_feedback_dataset", "feedback-v1", "exp-1", payload)

    with pytest.raises(FeedbackRetrainingDatasetConflictError, match="target"):
        service.build("exp-1", "model-v1", ["feedback-v1"])


def test_builder_accepts_confirmed_supplementary_measurement_source(builder):
    service, store = builder
    store.save("supplementary_measurement_batch", "supplement-measurement-v1", "exp-1", {
        "measurementBatchId": "supplement-measurement-v1",
        "experimentId": "exp-1",
        "status": "confirmed",
        "qualityGate": {
            "eligible": True,
            "feedbackDatasetVersion": "feedback-supplement-v1",
        },
    })
    store.save("experimental_feedback_dataset", "feedback-supplement-v1", "exp-1", {
        "feedbackDatasetVersion": "feedback-supplement-v1",
        "experimentId": "exp-1",
        "sourceType": "supplementary_measurement",
        "supplementaryMeasurementBatchId": "supplement-measurement-v1",
        "executionBatchId": "execution-v1",
        "parentModelVersion": "model-v1",
        "rows": [{
            "temperatureC": 37.8, "ph": 6.9, "stirringRpm": 201.0,
            "cultureHours": 48.0, "od600": 2.85,
            "replicateCount": 3, "batchCode": "SUP-01",
        }],
        "measurementIds": ["m1", "m2", "m3"],
        "sourceAssetIds": ["asset-1"],
        "createdAt": "2026-07-21T04:00:00+00:00",
    })

    derived = service.build("exp-1", "model-v1", ["feedback-supplement-v1"])

    assert derived.feedbackRowCount == 1
    assert derived.rows[-1]["od600"] == pytest.approx(2.85)


def test_builder_rejects_unconfirmed_supplementary_measurement_source(builder):
    service, store = builder
    store.save("supplementary_measurement_batch", "supplement-measurement-bad", "exp-1", {
        "measurementBatchId": "supplement-measurement-bad",
        "experimentId": "exp-1",
        "status": "needsReview",
        "qualityGate": {"eligible": False, "feedbackDatasetVersion": None},
    })
    store.save("experimental_feedback_dataset", "feedback-supplement-bad", "exp-1", {
        "feedbackDatasetVersion": "feedback-supplement-bad",
        "experimentId": "exp-1",
        "sourceType": "supplementary_measurement",
        "supplementaryMeasurementBatchId": "supplement-measurement-bad",
        "parentModelVersion": "model-v1",
        "rows": [{"temperatureC": 37.8, "ph": 6.9, "stirringRpm": 201.0, "od600": 2.85}],
    })

    with pytest.raises(FeedbackRetrainingDatasetConflictError, match="confirmed and eligible"):
        service.build("exp-1", "model-v1", ["feedback-supplement-bad"])
