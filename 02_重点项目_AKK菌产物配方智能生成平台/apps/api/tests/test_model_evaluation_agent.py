from copy import deepcopy

import pytest

from app.model_evaluation.agent import ModelEvaluationAgent
from app.model_registry.contracts import PromotedModelRecord
from app.research.contracts import ResearchCampaign, ResearchTrial
from app.services.experiment_data_store import SqliteExperimentDataStore


def model_record(version: str = "model-v1") -> PromotedModelRecord:
    return PromotedModelRecord(
        modelVersion=version,
        experimentId="exp-eval",
        campaignId="campaign-v1",
        trialId="trial-v1",
        artifactFingerprint="sha256:" + "a" * 64,
        artifactUri="artifact://models/" + "a" * 64,
        datasetSnapshotId="dataset-v1",
        datasetFingerprint="sha256:feature-input:sha256:feature-output",
        runnerKey="sklearn-time-series-modeling-v2",
        modelType="Ridge",
        featureNames=["temperature_c", "ph"],
        targetField="od600",
        featureRanges={
            "temperature_c": {"min": 35, "max": 39},
            "ph": {"min": 6.7, "max": 7.2},
        },
        metrics={"r2": 0.92, "mae": 0.04, "rmse": 0.05},
        approvedBy="owner",
        approvalReason="quality gates passed",
        approvedAt="2026-07-21T00:00:00+00:00",
    )


def model_card(*, drift: float = 0.2, coverage: float = 1.0) -> dict:
    train_stats = {
        "temperature_c": {"mean": 37.0, "std": 1.0, "min": 35.0, "max": 39.0},
        "ph": {"mean": 6.9, "std": 0.2, "min": 6.7, "max": 7.2},
    }
    holdout_stats = {
        "temperature_c": {"mean": 37.0 + drift, "std": 0.8, "min": 35.2, "max": 38.8},
        "ph": {"mean": 6.9 + drift * 0.2, "std": 0.18, "min": 6.72, "max": 7.18},
    }
    return {
        "schemaVersion": "1.0",
        "algorithm": "ridge",
        "modelType": "Ridge",
        "parameters": {"alpha": 0.1},
        "randomState": 42,
        "datasetSnapshotId": "dataset-v1",
        "datasetFingerprint": "sha256:feature-input:sha256:feature-output",
        "featureNames": ["temperature_c", "ph"],
        "targetField": "od600",
        "splitStrategy": "ordered_holdout_with_expanding_window_cv",
        "shuffle": False,
        "trainRows": 48,
        "holdoutRows": 12,
        "crossValidationFolds": [],
        "crossValidationMean": {"r2": 0.9, "mae": 0.05, "rmse": 0.06},
        "crossValidationStd": {"r2": 0.04, "mae": 0.01, "rmse": 0.01},
        "holdoutMetrics": {"r2": 0.92, "mae": 0.04, "rmse": 0.05},
        "holdoutObservations": [
            {"rowIndex": i, "actual": 0.5 + i * 0.1, "predicted": 0.49 + i * 0.1, "residual": 0.01}
            for i in range(12)
        ],
        "residualDiagnostics": {
            "meanResidual": 0.01,
            "residualStd": 0.005,
            "meanAbsoluteResidual": 0.01,
            "maxAbsoluteResidual": 0.02,
            "lag1Autocorrelation": 0.1,
            "predictionResidualCorrelation": 0.05,
        },
        "featureRanges": {
            "temperature_c": {"min": 35.0, "max": 39.0},
            "ph": {"min": 6.7, "max": 7.2},
        },
        "trainFeatureStats": train_stats,
        "holdoutFeatureStats": holdout_stats,
        "holdoutRangeCoverage": {
            "temperature_c": coverage,
            "ph": coverage,
        },
        "featureEffects": [
            {"feature": "temperature_c", "effect": 0.8, "normalizedImportance": 0.7, "method": "standardized_coefficient"},
            {"feature": "ph", "effect": -0.3, "normalizedImportance": 0.3, "method": "standardized_coefficient"},
        ],
        "targetRange": {"min": 0.1, "max": 1.8, "std": 0.5},
        "pythonVersion": "3.10",
        "sklearnVersion": "1.7.2",
        "limitations": ["研发用途"],
    }


def campaign(card: dict) -> ResearchCampaign:
    trial = ResearchTrial(
        trialId="trial-v1",
        sequence=1,
        commandId="trial-command",
        requestFingerprint="sha256:req",
        hypothesis="trusted candidate",
        parameterPatch={"algorithm": "ridge"},
        metrics={"r2": 0.92, "mae": 0.04, "rmse": 0.05},
        primaryScore=0.92,
        status="keep",
        comparedToTrialId=None,
        deltaFromBestBefore=0.2,
        deltaFromBaseline=0.2,
        fixedBudgetSeconds=30,
        durationSeconds=1.0,
        artifactFingerprint="sha256:" + "a" * 64,
        artifactUri="artifact://models/" + "a" * 64,
        runnerKey="sklearn-time-series-modeling-v2",
        datasetFingerprint="sha256:feature-input:sha256:feature-output",
        featureNames=["temperature_c", "ph"],
        targetField="od600",
        modelType="Ridge",
        featureRanges={
            "temperature_c": {"min": 35, "max": 39},
            "ph": {"min": 6.7, "max": 7.2},
        },
        modelCard=card,
        createdAt="2026-07-21T00:00:00+00:00",
    )
    return ResearchCampaign(
        campaignId="campaign-v1",
        experimentId="exp-eval",
        createCommandId="create",
        requestFingerprint="sha256:campaign",
        agentKey="modeling",
        agentVersion="1",
        datasetSnapshotId="dataset-v1",
        evaluationHarnessHash="sha256:harness",
        primaryMetric="r2",
        direction="maximize",
        fixedBudgetSeconds=30,
        minimumImprovement=0.01,
        promotionThresholds={"r2": 0.75},
        baselineTrialId="trial-v1",
        bestTrialId="trial-v1",
        status="completed",
        trials=[trial],
        promotion={
            "trialId": "trial-v1",
            "status": "approved",
            "operator": "owner",
            "reason": "passed",
            "gateChecks": {"all": True},
            "promotedModelVersion": "model-v1",
            "createdAt": "2026-07-21T00:00:00+00:00",
        },
        createdAt="2026-07-21T00:00:00+00:00",
        updatedAt="2026-07-21T00:00:00+00:00",
        mode="real_runner",
        runnerKey="sklearn-time-series-modeling-v2",
    )


class Registry:
    def __init__(self):
        self.record = model_record()

    def latest(self, experiment_id):
        return self.record


class Research:
    def __init__(self, value):
        self.value = value

    def get(self, experiment_id, campaign_id):
        return self.value


class Artifacts:
    def verify(self, fingerprint):
        return True


class Workspace:
    def __init__(self):
        self.applied = None

    def apply_model_evaluation(self, report, model_type):
        self.applied = (report, model_type)


def test_evaluation_calculates_residual_drift_interval_and_human_gate(tmp_path) -> None:
    registry = Registry()
    workspace = Workspace()
    store = SqliteExperimentDataStore(tmp_path / "data.db", tmp_path / "objects")
    agent = ModelEvaluationAgent(
        registry, Research(campaign(model_card())), Artifacts(), workspace, store,
    )

    report = agent.create_report("exp-eval")

    assert report.status == "needsReview"
    assert report.recommendedAdmission is True
    assert report.admissionAllowed is False
    assert report.reliabilityScore >= 0.7
    assert report.predictionInterval.sampleCount == 12
    assert report.predictionInterval.margin > 0
    assert len(report.driftDiagnostics) == 2
    with pytest.raises(ValueError, match="human confirmation"):
        agent.assert_simulation_ready("exp-eval")

    confirmed = agent.review(
        "exp-eval", report.reportId, "approved", "model-owner",
        "残差、漂移、覆盖率和适用边界均已复核",
    )
    assert confirmed.status == "confirmed"
    assert confirmed.admissionAllowed is True
    assert workspace.applied[0].reportId == report.reportId
    assert agent.assert_simulation_ready("exp-eval").reportId == report.reportId


def test_high_drift_blocks_admission_and_cannot_be_approved(tmp_path) -> None:
    card = model_card(drift=4.0, coverage=0.2)
    agent = ModelEvaluationAgent(
        Registry(), Research(campaign(card)), Artifacts(), Workspace(), None,
    )

    report = agent.create_report("exp-eval")

    assert report.recommendedAdmission is False
    assert any("漂移" in reason or "覆盖" in reason for reason in report.admissionReasons)
    with pytest.raises(ValueError, match="does not recommend"):
        agent.review(
            "exp-eval", report.reportId, "approved", "owner", "仍尝试放行",
        )
    rejected = agent.review(
        "exp-eval", report.reportId, "rejected", "owner", "漂移过高，补充新批次",
    )
    assert rejected.status == "rejected" and not rejected.admissionAllowed


def test_report_recovers_and_becomes_stale_when_promoted_model_changes(tmp_path) -> None:
    registry = Registry()
    store = SqliteExperimentDataStore(tmp_path / "data.db", tmp_path / "objects")
    first = ModelEvaluationAgent(
        registry, Research(campaign(model_card())), Artifacts(), Workspace(), store,
    )
    report = first.create_report("exp-eval")
    first.review(
        "exp-eval", report.reportId, "approved", "owner", "质量证据已复核",
    )

    recovered = ModelEvaluationAgent(
        registry, Research(campaign(model_card())), Artifacts(), Workspace(), store,
    )
    assert recovered.latest_report("exp-eval").status == "confirmed"
    registry.record = model_record("model-v2")
    with pytest.raises(ValueError, match="stale"):
        recovered.assert_simulation_ready("exp-eval")
