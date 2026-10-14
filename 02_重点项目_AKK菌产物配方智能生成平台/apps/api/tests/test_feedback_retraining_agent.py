from types import SimpleNamespace

import pytest

from app.feedback_retraining.agent import (
    FeedbackRetrainingAgent,
    FeedbackRetrainingConflictError,
)
from app.feedback_retraining.contracts import (
    FeedbackRetrainingCreate,
    FeedbackRetrainingReview,
)
from app.feedback_retraining.contracts import FeedbackDerivedDataset
from app.services.experiment_data_store import SqliteExperimentDataStore


class FakeBuilder:
    def __init__(self):
        self.dataset = FeedbackDerivedDataset(
            datasetId="feedback-derived-v1",
            experimentId="exp-1",
            parentModelVersion="model-v1",
            parentDatasetSnapshotId="dataset-parent-v1",
            parentDatasetFingerprint="sha256:parent",
            feedbackDatasetVersions=["feedback-1", "feedback-2", "feedback-3"],
            featureNames=["temperature_c", "ph"],
            targetField="od600",
            historicalRowCount=20,
            feedbackRowCount=3,
            trainingFeedbackRowCount=0,
            externalHoldoutRowCount=3,
            holdoutStartIndex=20,
            totalRowCount=23,
            rows=[{"temperature_c": 37.0, "ph": 6.9, "od600": 2.0}] * 23,
            datasetFingerprint="sha256:derived",
            createdAt="2026-07-21T00:00:00+00:00",
        )

    def build(self, experiment_id, parent_model_version, versions):
        assert experiment_id == "exp-1"
        assert parent_model_version == "model-v1"
        assert versions == ["feedback-1", "feedback-2", "feedback-3"]
        return self.dataset

    def get(self, experiment_id, dataset_id):
        assert experiment_id == "exp-1"
        assert dataset_id == self.dataset.datasetId
        return self.dataset


class FakeResearchService:
    def __init__(self, registry):
        self.registry = registry
        self.campaign = None
        self.promoteCalls = 0

    def create(self, experiment_id, request):
        baseline = SimpleNamespace(
            trialId="baseline", metrics={"r2": 0.70, "mae": 0.20, "rmse": 0.25},
            deltaFromBaseline=0.0, artifactFingerprint="sha256:baseline",
            artifactUri="artifact://models/baseline", modelType="GradientBoostingRegressor",
            featureNames=["temperature_c", "ph"], targetField="od600",
            featureRanges={}, datasetFingerprint="sha256:derived", runnerKey="runner",
        )
        self.campaign = SimpleNamespace(
            campaignId="research-feedback-v1", experimentId=experiment_id,
            trials=[baseline], baselineTrialId="baseline", bestTrialId="baseline",
            minimumImprovement=request.minimumImprovement,
            promotionThresholds={"r2": 0.75, "mae": 0.20},
            datasetSnapshotId=request.datasetSnapshotId,
        )
        return self.campaign

    def run_trial(self, experiment_id, campaign_id, request):
        scores = {"ridge": 0.76, "random_forest": 0.81, "gradient_boosting": 0.79}
        r2 = scores[request.parameterPatch["algorithm"]]
        trial = SimpleNamespace(
            trialId=f"trial-{request.parameterPatch['algorithm']}",
            metrics={"r2": r2, "mae": 0.14, "rmse": 0.18},
            deltaFromBaseline=r2 - 0.70,
            artifactFingerprint="sha256:" + request.parameterPatch["algorithm"],
            artifactUri="artifact://models/" + request.parameterPatch["algorithm"],
            modelType=request.parameterPatch["algorithm"],
            featureNames=["temperature_c", "ph"], targetField="od600",
            featureRanges={}, datasetFingerprint="sha256:derived", runnerKey="runner",
        )
        self.campaign.trials.append(trial)
        if r2 > next(item for item in self.campaign.trials if item.trialId == self.campaign.bestTrialId).metrics["r2"]:
            self.campaign.bestTrialId = trial.trialId
        return trial

    def get(self, experiment_id, campaign_id):
        return self.campaign

    def promote(self, experiment_id, campaign_id, request):
        self.promoteCalls += 1
        self.registry.current = SimpleNamespace(
            modelVersion="model-modeling-v2", experimentId=experiment_id,
        )
        self.campaign.promotion = SimpleNamespace(
            promotedModelVersion="model-modeling-v2", status=request.decision,
        )
        return self.campaign


class FakeRegistry:
    def __init__(self):
        self.current = SimpleNamespace(
            modelVersion="model-v1", experimentId="exp-1",
            artifactFingerprint="sha256:parent-artifact",
            artifactUri="artifact://models/parent-artifact",
        )

    def latest(self, experiment_id):
        return self.current

    def get(self, experiment_id, model_version):
        return self.current if self.current.modelVersion == model_version else None


@pytest.fixture()
def setup_agent(tmp_path):
    store = SqliteExperimentDataStore(tmp_path / "runs.db", tmp_path / "objects")
    registry = FakeRegistry()
    research = FakeResearchService(registry)
    evaluation_reports = []
    evaluation = SimpleNamespace(create_report=lambda experiment_id: evaluation_reports.append(experiment_id) or SimpleNamespace(reportId="eval-v2"))
    agent = FeedbackRetrainingAgent(
        store=store,
        dataset_builder=FakeBuilder(),
        registry=registry,
        research_service=research,
        artifact_store=SimpleNamespace(verify=lambda fingerprint: True),
        model_evaluation=evaluation,
        incumbent_evaluator=lambda parent, dataset: {"r2": 0.72, "mae": 0.19, "rmse": 0.24},
    )
    return agent, store, registry, research, evaluation_reports


def _request():
    return FeedbackRetrainingCreate(
        commandId="retrain-command-1",
        parentModelVersion="model-v1",
        feedbackDatasetVersions=["feedback-1", "feedback-2", "feedback-3"],
        fixedBudgetSeconds=30,
    )


def test_retraining_activity_is_idempotent_and_keeps_parent_model_before_review(setup_agent):
    agent, _store, registry, _research, _reports = setup_agent
    first = agent.create("exp-1", _request())
    second = agent.create("exp-1", _request())

    assert first.runId == second.runId
    assert first.status == "running"
    assert first.derivedDatasetId == "feedback-derived-v1"
    assert registry.latest("exp-1").modelVersion == "model-v1"
    assert first.stages[0].status == "completed"
    assert first.stages[1].status == "running"


def test_retraining_compares_three_candidates_with_incumbent_then_waits_for_human(setup_agent):
    agent, _store, registry, _research, _reports = setup_agent
    run = agent.create("exp-1", _request())
    run = agent.advance("exp-1", run.runId)
    assert run.incumbentMetrics["r2"] == 0.72
    run = agent.advance("exp-1", run.runId)
    assert len(run.candidates) == 3
    assert _research.campaign.minimumImprovement == 0
    run = agent.advance("exp-1", run.runId)

    assert run.status == "needsReview"
    assert run.championTrialId == "trial-random_forest"
    assert run.promotionGate.eligible is True
    assert run.promotionGate.checks["improvesIncumbentR2"] is True
    assert registry.latest("exp-1").modelVersion == "model-v1"


def test_human_approval_promotes_candidate_and_creates_pending_evaluation(setup_agent):
    agent, store, registry, research, reports = setup_agent
    run = agent.create("exp-1", _request())
    for _ in range(3):
        run = agent.advance("exp-1", run.runId)

    approved = agent.review(
        "exp-1", run.runId,
        FeedbackRetrainingReview(
            decision="approved", operator="研发负责人",
            reason="外部反馈留出集和模型产物均已复核",
        ),
    )

    assert approved.status == "completed"
    assert approved.promotedModelVersion == "model-modeling-v2"
    assert approved.evaluationReportId == "eval-v2"
    assert registry.latest("exp-1").modelVersion == "model-modeling-v2"
    assert research.promoteCalls == 1
    assert reports == ["exp-1"]
    restored = FeedbackRetrainingAgent(
        store, FakeBuilder(), registry, research,
        SimpleNamespace(verify=lambda fingerprint: True),
        SimpleNamespace(create_report=lambda _: None),
        lambda *_: {},
    ).get("exp-1", run.runId)
    assert restored.status == "completed"


def test_approval_is_blocked_if_incumbent_model_changed(setup_agent):
    agent, _store, registry, _research, _reports = setup_agent
    run = agent.create("exp-1", _request())
    for _ in range(3):
        run = agent.advance("exp-1", run.runId)
    registry.current = SimpleNamespace(modelVersion="model-other", experimentId="exp-1")

    with pytest.raises(FeedbackRetrainingConflictError, match="changed"):
        agent.review(
            "exp-1", run.runId,
            FeedbackRetrainingReview(
                decision="approved", operator="研发负责人",
                reason="尝试批准过期候选",
            ),
        )


def test_each_candidate_reports_its_own_artifact_verification(setup_agent):
    agent, _store, _registry, _research, _reports = setup_agent
    agent.artifacts = SimpleNamespace(
        verify=lambda fingerprint: not fingerprint.endswith("ridge")
    )
    run = agent.create("exp-1", _request())
    run = agent.advance("exp-1", run.runId)
    run = agent.advance("exp-1", run.runId)

    verification = {
        candidate.trialId: candidate.artifactVerified
        for candidate in run.candidates
    }
    assert verification["trial-ridge"] is False
    assert verification["trial-random_forest"] is True
