from pathlib import Path

import numpy as np

from app.research.artifacts import ContentAddressedModelArtifactStore
from app.research.runner import ResearchEvaluationContext
from app.research.contracts import ResearchCampaignCreate, ResearchTrialCreate
from app.research.service import ResearchCampaignService
from app.research.sklearn_runner import NumericTrainingDataset, SklearnResearchRunner
from app.research.store import SqliteResearchCampaignStore
from app.model_registry.store import SqlitePromotedModelRegistry
from app.model_registry.inference import PromotedModelInferenceService
from app.research.contracts import ResearchPromotionRequest


def dataset() -> NumericTrainingDataset:
    x = np.arange(0, 60, dtype=float)
    return NumericTrainingDataset(
        experimentId="exp-real", snapshotId="snapshot-real", datasetFingerprint="sha256:dataset123",
        featureNames=["temperature", "ph"], targetField="od600",
        X=np.column_stack([x, 6.5 + np.sin(x / 10)]), y=0.04 * x + 0.3 * np.sin(x / 10),
    )


def test_sklearn_runner_fits_real_model_calculates_metrics_and_writes_artifact(tmp_path) -> None:
    store = ContentAddressedModelArtifactStore(tmp_path / "artifacts")
    runner = SklearnResearchRunner(lambda experiment_id, snapshot_id: dataset(), store)
    outcome = runner.evaluate(
        {"mae": 9.0, "rmse": 9.0, "r2": -1.0}, {"nEstimators": 80, "maxDepth": 3}, 30,
        ResearchEvaluationContext(experimentId="exp-real", campaignId="campaign-1", datasetSnapshotId="snapshot-real", trialSequence=1),
    )
    assert outcome.errorMessage is None
    assert set(outcome.metrics) == {"mae", "rmse", "r2"}
    assert outcome.metrics["mae"] < 1.0
    assert outcome.artifactFingerprint.startswith("sha256:")
    assert outcome.artifactUri.startswith("artifact://models/")
    artifact_hash = outcome.artifactFingerprint.split(":", 1)[1]
    assert (tmp_path / "artifacts" / f"{artifact_hash}.joblib").exists()
    assert (tmp_path / "artifacts" / f"{artifact_hash}.json").exists()
    assert outcome.modelCard is not None
    assert outcome.modelCard["splitStrategy"] == "ordered_holdout_with_expanding_window_cv"
    assert outcome.modelCard["trainRows"] == 48
    assert outcome.modelCard["holdoutRows"] == 12
    assert len(outcome.modelCard["crossValidationFolds"]) >= 2
    assert set(outcome.modelCard["crossValidationMean"]) == {"mae", "rmse", "r2"}
    assert outcome.modelCard["algorithm"] == "gradient_boosting"
    assert len(outcome.modelCard["holdoutObservations"]) == 12
    assert set(outcome.modelCard["residualDiagnostics"]) == {
        "meanResidual", "residualStd", "meanAbsoluteResidual",
        "maxAbsoluteResidual", "lag1Autocorrelation",
        "predictionResidualCorrelation",
    }
    assert set(outcome.modelCard["trainFeatureStats"]) == {"temperature", "ph"}
    assert set(outcome.modelCard["holdoutRangeCoverage"]) == {"temperature", "ph"}
    assert len(outcome.modelCard["featureEffects"]) == 2
    assert outcome.modelCard["holdoutDiagnostics"]["r2Interpretation"] in {
        "standard", "unstable_low_variance_holdout",
    }
    assert outcome.modelCard["holdoutDiagnostics"]["normalizedMaeByTrainRange"] >= 0


def test_sklearn_runner_flags_r2_as_unstable_for_plateau_holdout(tmp_path) -> None:
    x = np.arange(0, 60, dtype=float)
    plateau = np.concatenate([np.linspace(0.1, 2.8, 48), np.linspace(2.85, 2.86, 12)])
    data = NumericTrainingDataset(
        experimentId="exp-plateau", snapshotId="snapshot-plateau",
        datasetFingerprint="sha256:plateau", featureNames=["time"], targetField="od600",
        X=x[:, None], y=plateau,
    )
    runner = SklearnResearchRunner(
        lambda *_: data, ContentAddressedModelArtifactStore(tmp_path / "artifacts"),
    )

    outcome = runner.evaluate(
        {}, {"algorithm": "gradient_boosting"}, 30,
        ResearchEvaluationContext(
            experimentId="exp-plateau", campaignId="campaign-plateau",
            datasetSnapshotId="snapshot-plateau", trialSequence=1,
        ),
    )

    diagnostic = outcome.modelCard["holdoutDiagnostics"]
    assert diagnostic["r2Stable"] is False
    assert diagnostic["r2Interpretation"] == "unstable_low_variance_holdout"
    assert any("R²" in item for item in outcome.modelCard["limitations"])


def test_sklearn_runner_compares_supported_algorithms_with_same_time_protocol(tmp_path) -> None:
    runner = SklearnResearchRunner(
        lambda *_: dataset(),
        ContentAddressedModelArtifactStore(tmp_path / "artifacts"),
    )
    outcomes = {
        algorithm: runner.evaluate(
            {},
            {"algorithm": algorithm},
            30,
            ResearchEvaluationContext(
                experimentId="exp-real",
                campaignId="campaign-algorithms",
                datasetSnapshotId="snapshot-real",
                trialSequence=index,
            ),
        )
        for index, algorithm in enumerate(
            ["ridge", "random_forest", "gradient_boosting"], start=1,
        )
    }
    assert all(outcome.errorMessage is None for outcome in outcomes.values())
    assert {outcome.modelCard["algorithm"] for outcome in outcomes.values()} == set(outcomes)
    assert {outcome.modelType for outcome in outcomes.values()} == {
        "Ridge", "RandomForestRegressor", "GradientBoostingRegressor",
    }
    assert all(
        np.isfinite(list(outcome.metrics.values())).all()
        for outcome in outcomes.values()
    )


def test_sklearn_runner_uses_explicit_confirmed_feedback_holdout(tmp_path) -> None:
    explicit = dataset()
    explicit.holdoutStartIndex = 55
    explicit.holdoutSource = "confirmed_feedback_batches"
    runner = SklearnResearchRunner(
        lambda *_: explicit,
        ContentAddressedModelArtifactStore(tmp_path / "artifacts"),
    )

    outcome = runner.evaluate(
        {}, {"algorithm": "ridge"}, 30,
        ResearchEvaluationContext(
            experimentId="exp-real", campaignId="feedback-campaign",
            datasetSnapshotId="snapshot-real", trialSequence=1,
        ),
    )

    assert outcome.errorMessage is None
    assert outcome.modelCard["trainRows"] == 55
    assert outcome.modelCard["holdoutRows"] == 5
    assert outcome.modelCard["holdoutSource"] == "confirmed_feedback_batches"
    assert outcome.modelCard["holdoutObservations"][0]["rowIndex"] == 55


def test_artifact_store_is_content_addressed_and_refuses_unverified_load(tmp_path) -> None:
    store = ContentAddressedModelArtifactStore(tmp_path / "artifacts")
    first = store.save({"model": "trusted"}, {"datasetFingerprint": "sha256:data", "sklearnVersion": "test"})
    second = store.save({"model": "trusted"}, {"datasetFingerprint": "sha256:data", "sklearnVersion": "test"})
    assert first.fingerprint == second.fingerprint
    path = Path(first.localPath)
    path.write_bytes(path.read_bytes() + b"tampered")
    try:
        store.verify(first.fingerprint)
    except ValueError as exc:
        assert "integrity" in str(exc)
    else:
        raise AssertionError("tampered artifact must fail integrity verification")


def test_sklearn_runner_rejects_too_small_or_non_finite_dataset(tmp_path) -> None:
    bad = dataset()
    bad.X = bad.X[:5]
    bad.y = bad.y[:5]
    runner = SklearnResearchRunner(lambda *_: bad, ContentAddressedModelArtifactStore(tmp_path / "artifacts"))
    outcome = runner.evaluate({}, {}, 30, ResearchEvaluationContext(experimentId="e", campaignId="c", datasetSnapshotId="s", trialSequence=0))
    assert outcome.errorMessage and "at least" in outcome.errorMessage
    assert outcome.artifactUri is None


def test_real_campaign_trains_and_records_a_real_baseline_artifact(tmp_path) -> None:
    runner = SklearnResearchRunner(lambda *_: dataset(), ContentAddressedModelArtifactStore(tmp_path / "artifacts"))
    service = ResearchCampaignService(SqliteResearchCampaignStore(":memory:"), runner)
    campaign = service.create("exp-real", ResearchCampaignCreate(
        commandId="create-real-1", agentKey="researchExperiment", datasetSnapshotId="snapshot-real",
        baselineMetrics={"mae": 99, "rmse": 99, "r2": -1}, primaryMetric="r2", direction="maximize",
        fixedBudgetSeconds=30, minimumImprovement=0.01, promotionThresholds={"r2": 0.1},
    ))
    baseline = campaign.trials[0]
    assert campaign.mode == "real_runner"
    assert campaign.runnerKey == "sklearn-time-series-modeling-v2"
    assert baseline.metrics != {"mae": 99, "rmse": 99, "r2": -1}
    assert baseline.artifactUri and baseline.datasetFingerprint == "sha256:dataset123"
    assert baseline.featureNames == ["temperature", "ph"]
    assert baseline.featureRanges["temperature"] == {"min": 0.0, "max": 59.0}


def test_approved_real_baseline_is_registered_for_inference(tmp_path) -> None:
    registry = SqlitePromotedModelRegistry(tmp_path / "models.db")
    artifacts = ContentAddressedModelArtifactStore(tmp_path / "artifacts")
    runner = SklearnResearchRunner(lambda *_: dataset(), artifacts)
    service = ResearchCampaignService(SqliteResearchCampaignStore(":memory:"), runner, model_registry=registry)
    campaign = service.create("exp-real", ResearchCampaignCreate(
        commandId="create-promote", agentKey="researchExperiment", datasetSnapshotId="snapshot-real",
        baselineMetrics={"mae": 99, "rmse": 99, "r2": -1}, primaryMetric="r2", direction="maximize",
        fixedBudgetSeconds=30, minimumImprovement=0, promotionThresholds={"r2": -10, "mae": 10},
    ))
    candidate = service.run_trial(
        "exp-real",
        campaign.campaignId,
        ResearchTrialCreate(
            commandId="ridge-candidate",
            hypothesis="线性关系使用 Ridge 进行时间外推",
            parameterPatch={"algorithm": "ridge", "alpha": 0.01},
        ),
    )
    promoted = service.promote("exp-real", campaign.campaignId, ResearchPromotionRequest(
        trialId=candidate.trialId, decision="approved", operator="研发负责人", reason="真实训练指标已复核",
    ))
    registered = registry.latest("exp-real")
    assert registered and registered.modelVersion == promoted.promotion.promotedModelVersion
    assert registered.artifactFingerprint == candidate.artifactFingerprint
    assert registered.featureRanges["ph"].min < registered.featureRanges["ph"].max
    prediction = PromotedModelInferenceService(registry, artifacts).predict(
        "exp-real", {"temperature": 30.0, "ph": 6.5 + float(np.sin(3))},
    )
    assert prediction.modelVersion == registered.modelVersion and prediction.targetField == "od600"


def test_real_model_promotion_has_non_overridable_quality_gates(tmp_path) -> None:
    runner = SklearnResearchRunner(
        lambda *_: dataset(),
        ContentAddressedModelArtifactStore(tmp_path / "artifacts"),
    )
    service = ResearchCampaignService(
        SqliteResearchCampaignStore(":memory:"),
        runner,
    )
    campaign = service.create("exp-real", ResearchCampaignCreate(
        commandId="create-hard-gate",
        agentKey="researchExperiment",
        datasetSnapshotId="snapshot-real",
        baselineMetrics={"mae": 99, "rmse": 99, "r2": -1},
        primaryMetric="r2",
        direction="maximize",
        fixedBudgetSeconds=30,
        minimumImprovement=0,
        promotionThresholds={"r2": -100, "mae": 100},
    ))
    campaign.trials[0].metrics["r2"] = -0.1
    service.store.save(campaign)

    import pytest
    from app.research.service import ResearchCampaignConflictError

    with pytest.raises(ResearchCampaignConflictError, match="promotion gates"):
        service.promote("exp-real", campaign.campaignId, ResearchPromotionRequest(
            trialId=campaign.baselineTrialId,
            decision="approved",
            operator="研发负责人",
            reason="即使用户阈值过低也不能绕过硬门禁",
        ))
