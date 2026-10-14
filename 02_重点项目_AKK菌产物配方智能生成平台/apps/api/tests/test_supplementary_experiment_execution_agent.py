from types import SimpleNamespace

import pytest

from app.schemas.optimization import OptimizationParameters
from app.services.experiment_data_store import SqliteExperimentDataStore
from app.supplementary_execution.agent import (
    SupplementaryExperimentExecutionAgent,
    SupplementaryExperimentExecutionConflictError,
)
from app.supplementary_execution.contracts import (
    SupplementaryExecutionAssetAttach,
    SupplementaryExecutionBatchCreate,
    SupplementaryExecutionReview,
    SupplementaryExecutionStart,
    SupplementaryExecutionStepUpdate,
)
from app.supplementary_design.contracts import SupplementaryExperimentCandidate


def _candidate(candidate_id="candidate-coverage"):
    return SupplementaryExperimentCandidate(
        candidateId=candidate_id,
        strategyKey="coverageRecovery",
        displayName="覆盖缺口修复方案",
        summary="补充模型分布覆盖",
        modelFeatureValues={"temperature_c": 37.8, "ph": 6.9},
        processParameters=OptimizationParameters(
            temperatureC=37.8, ph=6.9, cultureHours=48, stirringRpm=200,
        ),
        exploratoryPrediction=2.4,
        intervalLower=2.2,
        intervalUpper=2.6,
        intervalMethod="unreliable_model_empirical_holdout_margin",
        informationGainScore=0.7,
        boundaryRiskScore=0.4,
        addressesGaps=["覆盖不足"],
        evidence=["模型评估报告"],
    )


class DesignSource:
    def __init__(self):
        self.run = SimpleNamespace(
            runId="design-v1",
            experimentId="exp-1",
            status="approved",
            planVersion="supplement-plan-v1",
            modelVersion="model-v2",
            reportId="report-v2",
            reportInputFingerprint="sha256:report-v2",
            selectedCandidateIds=["candidate-coverage"],
            candidates=[_candidate()],
        )

    def get(self, experiment_id, run_id):
        return self.run


class FileSource:
    def __init__(self):
        self.asset = SimpleNamespace(
            assetId="asset-1", originalName="真实设备数据.csv",
            contentHash="sha256:file-1", parseStatus="parsed",
        )

    def get_file_asset(self, experiment_id, asset_id):
        return self.asset if experiment_id == "exp-1" and asset_id == "asset-1" else None

    def verify_asset_integrity(self, asset_id):
        return asset_id == "asset-1"


@pytest.fixture()
def agent(tmp_path):
    store = SqliteExperimentDataStore(tmp_path / "execution.db", tmp_path / "objects")
    design = DesignSource()
    registry = SimpleNamespace(latest=lambda experiment_id: SimpleNamespace(modelVersion="model-v2"))
    evaluation = SimpleNamespace(latest_report=lambda experiment_id: SimpleNamespace(
        reportId="report-v2", inputFingerprint="sha256:report-v2",
    ))
    return SupplementaryExperimentExecutionAgent(
        store=store,
        design_agent=design,
        registry=registry,
        evaluation_agent=evaluation,
        file_service=FileSource(),
    ), design, store


def _create():
    return SupplementaryExecutionBatchCreate(
        commandId="execution-command-v1",
        designRunId="design-v1",
        planVersion="supplement-plan-v1",
        candidateId="candidate-coverage",
        batchCode="SUP-20260721-01",
        scale="lab",
        operator="研发负责人",
        plannedAt="2026-07-22T08:00:00+08:00",
        replicateCount=3,
        samplingRequirements=["培养结束后采样", "每个目标指标至少三个独立重复"],
    )


def test_create_snapshots_approved_candidate_and_persists_idempotently(agent):
    execution, design, store = agent

    first = execution.create("exp-1", _create())
    second = execution.create("exp-1", _create())
    recovered = SupplementaryExperimentExecutionAgent(
        store, design,
        SimpleNamespace(latest=lambda _: SimpleNamespace(modelVersion="model-v2")),
        SimpleNamespace(latest_report=lambda _: SimpleNamespace(reportId="report-v2", inputFingerprint="sha256:report-v2")),
        FileSource(),
    )

    assert first.batchId == second.batchId
    assert first.status == "planned"
    assert first.planVersion == "supplement-plan-v1"
    assert first.frozenParameters.temperatureC == 37.8
    assert first.replicateCount == 3
    assert [step.stepKey for step in first.steps] == [
        "preparation", "equipmentCheck", "parameterExecution",
        "sampling", "dataArchive", "humanConfirmation",
    ]
    assert recovered.get("exp-1", first.batchId).requestFingerprint == first.requestFingerprint


def test_create_rejects_unapproved_stale_or_duplicate_plan_candidate(agent):
    execution, design, _store = agent
    first = execution.create("exp-1", _create())
    assert first.batchId

    duplicate = _create().model_copy(update={"commandId": "another", "batchCode": "SUP-02"})
    with pytest.raises(SupplementaryExperimentExecutionConflictError, match="already has an execution batch"):
        execution.create("exp-1", duplicate)

    design.run.status = "needsReview"
    with pytest.raises(SupplementaryExperimentExecutionConflictError, match="approved"):
        execution.create("exp-1", _create().model_copy(update={"candidateId": "candidate-other", "commandId": "third"}))


def test_steps_are_sequential_and_data_archive_requires_real_asset(agent):
    execution, _design, _store = agent
    batch = execution.create("exp-1", _create())
    started = execution.start("exp-1", batch.batchId, SupplementaryExecutionStart(operator="执行员", note="开始执行"))
    assert started.status == "inProgress"

    with pytest.raises(SupplementaryExperimentExecutionConflictError, match="previous step"):
        execution.update_step("exp-1", batch.batchId, "sampling", SupplementaryExecutionStepUpdate(operator="执行员", status="completed", note="越序"))

    for key in ["preparation", "equipmentCheck", "parameterExecution", "sampling"]:
        updated = execution.update_step("exp-1", batch.batchId, key, SupplementaryExecutionStepUpdate(operator="执行员", status="completed", note=f"{key} 已完成"))
    assert updated.status == "awaitingData"

    with pytest.raises(SupplementaryExperimentExecutionConflictError, match="data asset"):
        execution.update_step("exp-1", batch.batchId, "dataArchive", SupplementaryExecutionStepUpdate(operator="执行员", status="completed", note="尝试归档"))

    attached = execution.attach_assets("exp-1", batch.batchId, SupplementaryExecutionAssetAttach(operator="执行员", assetIds=["asset-1"], note="真实设备导出数据"))
    assert attached.assets[0].integrityVerified is True
    archived = execution.update_step("exp-1", batch.batchId, "dataArchive", SupplementaryExecutionStepUpdate(operator="执行员", status="completed", note="原始数据已归档"))
    assert archived.status == "inProgress"


def test_final_human_step_requires_review_and_completed_batch_is_immutable(agent):
    execution, _design, _store = agent
    batch = execution.start("exp-1", execution.create("exp-1", _create()).batchId, SupplementaryExecutionStart(operator="执行员", note="开始"))
    for key in ["preparation", "equipmentCheck", "parameterExecution", "sampling"]:
        batch = execution.update_step("exp-1", batch.batchId, key, SupplementaryExecutionStepUpdate(operator="执行员", status="completed", note="已完成"))
    execution.attach_assets("exp-1", batch.batchId, SupplementaryExecutionAssetAttach(operator="执行员", assetIds=["asset-1"], note="真实数据"))
    execution.update_step("exp-1", batch.batchId, "dataArchive", SupplementaryExecutionStepUpdate(operator="执行员", status="completed", note="归档完成"))
    awaiting = execution.update_step("exp-1", batch.batchId, "humanConfirmation", SupplementaryExecutionStepUpdate(operator="执行员", status="completed", note="提交人工复核"))
    assert awaiting.status == "needsReview"

    completed = execution.review("exp-1", batch.batchId, SupplementaryExecutionReview(decision="approved", operator="研发负责人", reason="步骤与原始数据完整"))
    assert completed.status == "completed"
    assert completed.completedAt is not None
    assert completed.disclaimer.endswith("不直接控制设备。")

    with pytest.raises(SupplementaryExperimentExecutionConflictError, match="terminal"):
        execution.attach_assets("exp-1", batch.batchId, SupplementaryExecutionAssetAttach(operator="执行员", assetIds=["asset-1"], note="重复修改"))


def test_rejection_reopens_human_confirmation_without_erasing_audit(agent):
    execution, _design, _store = agent
    batch = execution.start("exp-1", execution.create("exp-1", _create()).batchId, SupplementaryExecutionStart(operator="执行员", note="开始"))
    for key in ["preparation", "equipmentCheck", "parameterExecution", "sampling"]:
        batch = execution.update_step("exp-1", batch.batchId, key, SupplementaryExecutionStepUpdate(operator="执行员", status="completed", note="完成"))
    execution.attach_assets("exp-1", batch.batchId, SupplementaryExecutionAssetAttach(operator="执行员", assetIds=["asset-1"], note="设备文件"))
    for key in ["dataArchive", "humanConfirmation"]:
        batch = execution.update_step("exp-1", batch.batchId, key, SupplementaryExecutionStepUpdate(operator="执行员", status="completed", note="完成"))

    rejected = execution.review("exp-1", batch.batchId, SupplementaryExecutionReview(decision="rejected", operator="复核员", reason="补充设备异常说明"))
    assert rejected.status == "inProgress"
    assert rejected.steps[-1].status == "pending"
    assert any(event.eventType == "review_rejected" for event in rejected.events)
