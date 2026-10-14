import pytest

from app.research.contracts import ResearchCampaignCreate, ResearchPromotionRequest, ResearchTrialCreate
from app.research.service import ResearchCampaignConflictError, ResearchCampaignService
from app.research.store import SqliteResearchCampaignStore
from app.research.runner import ResearchEvaluationOutcome


def make_service(tmp_path) -> ResearchCampaignService:
    return ResearchCampaignService(SqliteResearchCampaignStore(tmp_path / "research.db"))


def test_campaign_starts_with_fixed_baseline_and_persists(tmp_path) -> None:
    service = make_service(tmp_path)
    campaign = service.create("exp-1", ResearchCampaignCreate(
        commandId="create-1", datasetSnapshotId="snapshot-v4", agentKey="modeling",
        baselineMetrics={"mae": 0.18, "rmse": 0.24, "r2": 0.78}, fixedBudgetSeconds=300,
    ))
    assert campaign.baselineTrialId == campaign.bestTrialId
    assert campaign.trials[0].status == "keep"
    assert campaign.evaluationHarnessHash.startswith("sha256:")
    restored = ResearchCampaignService(SqliteResearchCampaignStore(tmp_path / "research.db")).get("exp-1", campaign.campaignId)
    assert restored.model_dump() == campaign.model_dump()


def test_trials_are_idempotent_and_keep_or_discard_against_best(tmp_path) -> None:
    service = make_service(tmp_path)
    campaign = service.create("exp-1", ResearchCampaignCreate(commandId="create", datasetSnapshotId="snap", agentKey="modeling", baselineMetrics={"mae": 0.18, "rmse": 0.24, "r2": 0.78}))
    improved = service.run_trial("exp-1", campaign.campaignId, ResearchTrialCreate(commandId="trial-1", hypothesis="降低学习率提高泛化稳定性", parameterPatch={"learningRate": 0.03}))
    assert improved.status == "keep" and improved.deltaFromBestBefore > 0
    assert service.run_trial("exp-1", campaign.campaignId, ResearchTrialCreate(commandId="trial-1", hypothesis="降低学习率提高泛化稳定性", parameterPatch={"learningRate": 0.03})).trialId == improved.trialId
    discarded = service.run_trial("exp-1", campaign.campaignId, ResearchTrialCreate(commandId="trial-2", hypothesis="过度增加树深", parameterPatch={"maxDepth": 20}))
    assert discarded.status == "discard"
    assert service.get("exp-1", campaign.campaignId).status == "needsReview"


def test_evaluation_harness_and_dataset_are_immutable_within_campaign(tmp_path) -> None:
    service = make_service(tmp_path)
    campaign = service.create("exp-1", ResearchCampaignCreate(commandId="create", datasetSnapshotId="snap", agentKey="modeling", baselineMetrics={"mae": 0.18, "rmse": 0.24, "r2": 0.78}))
    with pytest.raises(ResearchCampaignConflictError, match="protected"):
        service.run_trial("exp-1", campaign.campaignId, ResearchTrialCreate(commandId="bad", hypothesis="修改评测集", parameterPatch={"datasetSnapshotId": "other"}))


def test_promotion_requires_metric_gate_and_explicit_human_approval(tmp_path) -> None:
    service = make_service(tmp_path)
    campaign = service.create("exp-1", ResearchCampaignCreate(commandId="create", datasetSnapshotId="snap", agentKey="modeling", baselineMetrics={"mae": 0.18, "rmse": 0.24, "r2": 0.78}, minimumImprovement=0.005))
    candidate = service.run_trial("exp-1", campaign.campaignId, ResearchTrialCreate(commandId="trial", hypothesis="调节学习率", parameterPatch={"learningRate": 0.03}))
    with pytest.raises(ResearchCampaignConflictError, match="human approval"):
        service.promote("exp-1", campaign.campaignId, ResearchPromotionRequest(trialId=candidate.trialId, decision="approved", operator="", reason=""))
    promoted = service.promote("exp-1", campaign.campaignId, ResearchPromotionRequest(trialId=candidate.trialId, decision="approved", operator="研发负责人", reason="指标提升且风险项已核对"))
    assert promoted.promotion.status == "approved"
    assert promoted.status == "completed"
    assert promoted.disclaimer == "研发实验建议"


def test_research_agent_proposes_one_bounded_change_per_iteration(tmp_path) -> None:
    service = make_service(tmp_path)
    campaign = service.create("exp-1", ResearchCampaignCreate(commandId="create", datasetSnapshotId="snap", agentKey="modeling", baselineMetrics={"mae": 0.18, "rmse": 0.24, "r2": 0.78}))
    proposal = service.propose_next("exp-1", campaign.campaignId, "auto-1")
    assert len(proposal.parameterPatch) == 1
    assert not (service.PROTECTED_PARAMETERS & proposal.parameterPatch.keys())


def test_real_runner_adapter_can_replace_mock_without_changing_campaign_logic(tmp_path) -> None:
    class Runner:
        mode = "real_runner"
        runnerKey = "sklearn-real-v1"
        def evaluate(self, baseline, parameter_patch, fixed_budget_seconds, context):
            return ResearchEvaluationOutcome({"mae": 0.16, "rmse": 0.22, "r2": 0.81}, 12.5)

    service = ResearchCampaignService(SqliteResearchCampaignStore(tmp_path / "real.db"), Runner())
    campaign = service.create("exp-1", ResearchCampaignCreate(commandId="create", datasetSnapshotId="snap", agentKey="modeling", baselineMetrics={"mae": 0.18, "rmse": 0.24, "r2": 0.78}))
    trial = service.run_trial("exp-1", campaign.campaignId, ResearchTrialCreate(commandId="real-1", hypothesis="真实 runner", parameterPatch={"learningRate": 0.02}))
    assert campaign.mode == "real_runner"
    assert trial.metrics["r2"] == 0.81 and trial.durationSeconds == 12.5
