from types import SimpleNamespace

import pytest

from app.schemas.optimization import OptimizationParameters
from app.services.experiment_data_store import SqliteExperimentDataStore
from app.supplementary_measurement.agent import (
    SupplementaryMeasurementHandoffAgent,
    SupplementaryMeasurementHandoffConflictError,
)
from app.supplementary_measurement.contracts import (
    SupplementaryMeasurementBatchCreate,
    SupplementaryMeasurementInput,
    SupplementaryMeasurementReview,
    SupplementaryMeasurementSubmission,
)


class ExecutionSource:
    def __init__(self):
        self.batch = SimpleNamespace(
            batchId="execution-v1", experimentId="exp-1", status="completed",
            planVersion="supplement-plan-v1", candidateId="candidate-v1",
            modelVersion="model-v2", reportId="report-v2", batchCode="SUP-01",
            frozenParameters=OptimizationParameters(
                temperatureC=37.8, ph=6.9, cultureHours=48, stirringRpm=200,
            ),
            assets=[SimpleNamespace(
                assetId="asset-1", originalName="device.csv",
                contentHash="sha256:file", integrityVerified=True,
            )],
        )

    def get(self, experiment_id, batch_id):
        return self.batch


@pytest.fixture()
def setup_agent(tmp_path):
    store = SqliteExperimentDataStore(tmp_path / "measurements.db", tmp_path / "objects")
    execution = ExecutionSource()
    registry = SimpleNamespace(get=lambda experiment_id, version: SimpleNamespace(
        modelVersion=version, targetField="od600",
        featureNames=["temperature_c", "ph", "agitation_rpm"],
    ))
    agent = SupplementaryMeasurementHandoffAgent(store, execution, registry)
    return agent, execution, store


def _create(command="measurement-create-v1"):
    return SupplementaryMeasurementBatchCreate(
        commandId=command, executionBatchId="execution-v1",
        operator="研发负责人",
    )


def _submission(*, asset_id="asset-1", replicates=3, contamination=False, abnormalities=None):
    return SupplementaryMeasurementSubmission(
        actualParameters=OptimizationParameters(
            temperatureC=37.8, ph=6.9, cultureHours=48, stirringRpm=200,
        ),
        measurements=[SupplementaryMeasurementInput(
            metricName="od600", value=2.8 + index * 0.05, unit="AU",
            replicate=index + 1, measuredAt="2026-07-22T10:00:00+08:00",
            method="分光光度计 600 nm", sourceAssetId=asset_id,
            isModelTarget=True,
        ) for index in range(replicates)],
        contaminationObserved=contamination,
        equipmentAbnormalities=abnormalities or [],
        notes="真实补实验测量录入",
    )


def test_create_requires_completed_execution_and_snapshots_lineage_idempotently(setup_agent):
    agent, execution, store = setup_agent
    first = agent.create("exp-1", _create())
    second = agent.create("exp-1", _create())
    recovered = SupplementaryMeasurementHandoffAgent(store, execution, agent.registry)

    assert first.measurementBatchId == second.measurementBatchId
    assert first.status == "draft"
    assert first.executionBatchId == "execution-v1"
    assert first.parentModelVersion == "model-v2"
    assert first.targetMetric == "od600"
    assert first.allowedSourceAssetIds == ["asset-1"]
    assert recovered.get("exp-1", first.measurementBatchId).planVersion == "supplement-plan-v1"


def test_create_rejects_incomplete_execution_and_duplicate_handoff(setup_agent):
    agent, execution, _store = setup_agent
    agent.create("exp-1", _create())
    with pytest.raises(SupplementaryMeasurementHandoffConflictError, match="already has"):
        agent.create("exp-1", _create("second-command"))
    execution.batch.batchId = "execution-v2"
    execution.batch.status = "needsReview"
    with pytest.raises(SupplementaryMeasurementHandoffConflictError, match="completed"):
        agent.create("exp-1", SupplementaryMeasurementBatchCreate(commandId="third", executionBatchId="execution-v2", operator="研发负责人"))


def test_submission_requires_execution_asset_and_builds_quality_gate(setup_agent):
    agent, _execution, _store = setup_agent
    batch = agent.create("exp-1", _create())
    with pytest.raises(SupplementaryMeasurementHandoffConflictError, match="source asset"):
        agent.submit("exp-1", batch.measurementBatchId, _submission(asset_id="asset-other"))

    submitted = agent.submit("exp-1", batch.measurementBatchId, _submission())
    assert submitted.status == "needsReview"
    assert submitted.qualityGate is not None
    assert submitted.qualityGate.checks["minimumTargetReplicates"] is True
    assert submitted.qualityGate.checks["sourceAssetsVerified"] is True
    assert submitted.qualityGate.checks["humanConfirmed"] is False
    assert submitted.qualityGate.eligible is False


def test_bad_target_or_quality_cannot_be_approved(setup_agent):
    agent, _execution, _store = setup_agent
    batch = agent.create("exp-1", _create())
    bad = _submission(contamination=True)
    submitted = agent.submit("exp-1", batch.measurementBatchId, bad)
    assert submitted.qualityGate.checks["noContamination"] is False

    with pytest.raises(SupplementaryMeasurementHandoffConflictError, match="quality gate"):
        agent.review("exp-1", batch.measurementBatchId, SupplementaryMeasurementReview(decision="approved", operator="复核员", reason="尝试绕过污染门禁"))


def test_human_approval_persists_compatible_feedback_dataset(setup_agent):
    agent, _execution, store = setup_agent
    batch = agent.create("exp-1", _create())
    submitted = agent.submit("exp-1", batch.measurementBatchId, _submission())
    confirmed = agent.review("exp-1", submitted.measurementBatchId, SupplementaryMeasurementReview(decision="approved", operator="复核员", reason="来源与三个重复测量均已核对"))

    assert confirmed.status == "confirmed"
    assert confirmed.qualityGate.eligible is True
    version = confirmed.qualityGate.feedbackDatasetVersion
    payload = store.get("experimental_feedback_dataset", version)
    assert payload["sourceType"] == "supplementary_measurement"
    assert payload["supplementaryMeasurementBatchId"] == confirmed.measurementBatchId
    assert payload["executionBatchId"] == "execution-v1"
    assert payload["parentModelVersion"] == "model-v2"
    assert payload["rows"][0]["od600"] == pytest.approx(2.85)
    assert payload["rows"][0]["replicateCount"] == 3


def test_rejection_preserves_measurements_without_creating_feedback_asset(setup_agent):
    agent, _execution, store = setup_agent
    batch = agent.create("exp-1", _create())
    submitted = agent.submit("exp-1", batch.measurementBatchId, _submission())
    rejected = agent.review("exp-1", submitted.measurementBatchId, SupplementaryMeasurementReview(decision="rejected", operator="复核员", reason="测量方法证明不足"))

    assert rejected.status == "rejected"
    assert len(rejected.measurements) == 3
    assert rejected.qualityGate.feedbackDatasetVersion is None
    assert store.list("experimental_feedback_dataset", "exp-1") == []
