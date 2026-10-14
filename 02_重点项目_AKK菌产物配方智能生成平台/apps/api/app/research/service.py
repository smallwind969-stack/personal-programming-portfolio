from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from uuid import uuid4

from app.agent_registry.builtin import agent_catalog
from app.research.contracts import ResearchCampaign, ResearchCampaignCreate, ResearchPromotion, ResearchPromotionRequest, ResearchTrial, ResearchTrialCreate
from app.research.store import SqliteResearchCampaignStore
from app.research.runner import DeterministicMockResearchRunner, ResearchEvaluationContext, ResearchEvaluationRunner
from app.model_registry.contracts import PromotedModelRecord
from app.model_registry.store import SqlitePromotedModelRegistry
from app.paths import project_path


class ResearchCampaignConflictError(RuntimeError): pass
class ResearchCampaignNotFoundError(LookupError): pass


def _now() -> str: return datetime.now(timezone.utc).isoformat()
def _hash(value) -> str: return "sha256:" + sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class ResearchCampaignService:
    PROTECTED_PARAMETERS = {"datasetSnapshotId", "evaluationHarness", "primaryMetric", "direction", "fixedBudgetSeconds"}
    ALLOWED_PARAMETERS = {
        "algorithm", "alpha", "nEstimators", "learningRate", "maxDepth",
        "minSamplesLeaf", "subsample",
    }

    def __init__(self, store: SqliteResearchCampaignStore, runner: ResearchEvaluationRunner | None = None,
                 runner_fallback_reason: str | None = None, model_registry: SqlitePromotedModelRegistry | None = None) -> None:
        self.store = store
        self.runner = runner or DeterministicMockResearchRunner()
        self.runnerFallbackReason = runner_fallback_reason
        self.modelRegistry = model_registry

    def create(self, experiment_id: str, request: ResearchCampaignCreate) -> ResearchCampaign:
        fingerprint = _hash(request.model_dump(mode="json"))
        existing = self.store.by_command(experiment_id, request.commandId)
        if existing:
            if existing.requestFingerprint != fingerprint: raise ResearchCampaignConflictError("commandId reused with a different campaign")
            return existing
        agent = agent_catalog.agent(request.agentKey)
        now = _now(); campaign_id = f"research-{uuid4().hex[:12]}"; baseline_id = f"trial-{uuid4().hex[:10]}"
        harness = _hash({"datasetSnapshotId": request.datasetSnapshotId, "metrics": sorted(request.baselineMetrics), "primaryMetric": request.primaryMetric, "direction": request.direction, "budget": request.fixedBudgetSeconds, "evaluator": self.runner.runnerKey})
        baseline_metrics = request.baselineMetrics
        baseline_outcome = None
        if self.runner.mode == "real_runner":
            baseline_outcome = self.runner.evaluate(request.baselineMetrics, {}, request.fixedBudgetSeconds,
                ResearchEvaluationContext(experimentId=experiment_id, campaignId=campaign_id,
                                          datasetSnapshotId=request.datasetSnapshotId, trialSequence=0))
            if baseline_outcome.errorMessage:
                raise ResearchCampaignConflictError(f"real baseline training failed: {baseline_outcome.errorMessage}")
            baseline_metrics = baseline_outcome.metrics
        baseline = ResearchTrial(trialId=baseline_id, sequence=0, commandId=request.commandId + ":baseline", requestFingerprint=fingerprint,
            hypothesis="固定评测器基线", parameterPatch={}, metrics=baseline_metrics, primaryScore=baseline_metrics[request.primaryMetric],
            status="keep", deltaFromBestBefore=0, deltaFromBaseline=0, fixedBudgetSeconds=request.fixedBudgetSeconds,
            durationSeconds=baseline_outcome.durationSeconds if baseline_outcome else 0,
            artifactFingerprint=baseline_outcome.artifactFingerprint if baseline_outcome and baseline_outcome.artifactFingerprint else _hash({"campaign": campaign_id, "trial": 0, "metrics": baseline_metrics}),
            artifactUri=baseline_outcome.artifactUri if baseline_outcome else None, runnerKey=self.runner.runnerKey,
            datasetFingerprint=baseline_outcome.datasetFingerprint if baseline_outcome else request.datasetSnapshotId,
            featureNames=(baseline_outcome.featureNames or []) if baseline_outcome else [], targetField=baseline_outcome.targetField if baseline_outcome else None,
            modelType=baseline_outcome.modelType if baseline_outcome else None,
            modelCard=baseline_outcome.modelCard if baseline_outcome else None, createdAt=now)
        if baseline_outcome:
            baseline.featureRanges = baseline_outcome.featureRanges or {}
        campaign = ResearchCampaign(campaignId=campaign_id, experimentId=experiment_id, createCommandId=request.commandId,
            requestFingerprint=fingerprint, agentKey=request.agentKey, agentVersion=agent.version, datasetSnapshotId=request.datasetSnapshotId,
            evaluationHarnessHash=harness, primaryMetric=request.primaryMetric, direction=request.direction,
            fixedBudgetSeconds=request.fixedBudgetSeconds, minimumImprovement=request.minimumImprovement,
            promotionThresholds=request.promotionThresholds, baselineTrialId=baseline_id, bestTrialId=baseline_id,
            status="active", trials=[baseline], createdAt=now, updatedAt=now, mode=self.runner.mode, runnerKey=self.runner.runnerKey,
            runnerFallbackReason=self.runnerFallbackReason)
        self.store.save(campaign); return campaign

    def get(self, experiment_id: str, campaign_id: str) -> ResearchCampaign:
        campaign = self.store.get(experiment_id, campaign_id)
        if not campaign: raise ResearchCampaignNotFoundError(campaign_id)
        return campaign

    def list(self, experiment_id: str) -> list[ResearchCampaign]: return self.store.list(experiment_id)

    def propose_next(self, experiment_id: str, campaign_id: str, command_id: str) -> ResearchTrialCreate:
        campaign = self.get(experiment_id, campaign_id)
        if campaign.status not in {"active", "needsReview"}: raise ResearchCampaignConflictError(f"campaign in {campaign.status} cannot propose trials")
        candidates = [
            ("使用 Ridge 建立线性可解释基线", {"algorithm": "ridge"}),
            ("使用随机森林比较非线性稳健性", {"algorithm": "random_forest"}),
            ("降低梯度提升学习率以改善时间外推稳定性", {"learningRate": 0.03}),
            ("限制树深度以降低过拟合风险", {"maxDepth": 2}),
            ("增加最小叶节点样本数", {"minSamplesLeaf": 3}),
        ]
        hypothesis, patch = candidates[(len(campaign.trials) - 1) % len(candidates)]
        return ResearchTrialCreate(commandId=command_id, hypothesis=hypothesis, parameterPatch=patch)

    def run_trial(self, experiment_id: str, campaign_id: str, request: ResearchTrialCreate) -> ResearchTrial:
        campaign = self.get(experiment_id, campaign_id)
        fingerprint = _hash(request.model_dump(mode="json"))
        existing = next((trial for trial in campaign.trials if trial.commandId == request.commandId), None)
        if existing:
            if existing.requestFingerprint != fingerprint: raise ResearchCampaignConflictError("commandId reused with a different trial")
            return existing
        protected = self.PROTECTED_PARAMETERS & request.parameterPatch.keys()
        if protected: raise ResearchCampaignConflictError(f"protected evaluation fields cannot change: {', '.join(sorted(protected))}")
        unknown = request.parameterPatch.keys() - self.ALLOWED_PARAMETERS
        if unknown:
            raise ResearchCampaignConflictError(
                f"unsupported modeling parameters: {', '.join(sorted(unknown))}"
            )
        if campaign.status not in {"active", "needsReview"}: raise ResearchCampaignConflictError(f"campaign in {campaign.status} cannot run trials")
        best = next(trial for trial in campaign.trials if trial.trialId == campaign.bestTrialId)
        baseline = campaign.trials[0]
        outcome = self.runner.evaluate(baseline.metrics, request.parameterPatch, campaign.fixedBudgetSeconds,
            ResearchEvaluationContext(experimentId=experiment_id, campaignId=campaign_id,
                                      datasetSnapshotId=campaign.datasetSnapshotId, trialSequence=len(campaign.trials)))
        metrics, duration, error = outcome.metrics, outcome.durationSeconds, outcome.errorMessage
        score = metrics[campaign.primaryMetric] if not error else 0.0
        delta_best = self._improvement(score, best.primaryScore, campaign.direction)
        delta_baseline = self._improvement(score, baseline.primaryScore, campaign.direction)
        status = "crash" if error else "keep" if delta_best > 0 else "discard"
        now = _now(); sequence = len(campaign.trials)
        trial = ResearchTrial(trialId=f"trial-{uuid4().hex[:10]}", sequence=sequence, commandId=request.commandId,
            requestFingerprint=fingerprint, hypothesis=request.hypothesis, parameterPatch=request.parameterPatch, metrics=metrics,
            primaryScore=score, status=status, comparedToTrialId=best.trialId, deltaFromBestBefore=round(delta_best, 6),
            deltaFromBaseline=round(delta_baseline, 6), fixedBudgetSeconds=campaign.fixedBudgetSeconds, durationSeconds=duration,
            artifactFingerprint=outcome.artifactFingerprint or _hash({"campaign": campaign_id, "sequence": sequence, "patch": request.parameterPatch, "metrics": metrics}),
            artifactUri=outcome.artifactUri, runnerKey=self.runner.runnerKey, datasetFingerprint=outcome.datasetFingerprint,
            featureNames=outcome.featureNames or [], targetField=outcome.targetField, modelType=outcome.modelType,
            featureRanges=outcome.featureRanges or {}, modelCard=outcome.modelCard,
            errorMessage=error, createdAt=now)
        campaign.trials.append(trial)
        if status == "keep": campaign.bestTrialId = trial.trialId
        current_best = trial if status == "keep" else best
        campaign.status = "needsReview" if current_best.deltaFromBaseline >= campaign.minimumImprovement else "active"
        campaign.updatedAt = now; self.store.save(campaign); return trial

    @staticmethod
    def _improvement(candidate: float, reference: float, direction: str) -> float:
        return candidate - reference if direction == "maximize" else reference - candidate

    def promote(self, experiment_id: str, campaign_id: str, request: ResearchPromotionRequest) -> ResearchCampaign:
        campaign = self.get(experiment_id, campaign_id)
        if not request.operator.strip() or not request.reason.strip(): raise ResearchCampaignConflictError("human approval requires operator and reason")
        trial = next((item for item in campaign.trials if item.trialId == request.trialId), None)
        if not trial: raise ResearchCampaignNotFoundError(request.trialId)
        checks = {"isBest": trial.trialId == campaign.bestTrialId, "minimumImprovement": trial.deltaFromBaseline >= campaign.minimumImprovement,
                  **{f"threshold:{key}": (trial.metrics.get(key, float("-inf")) >= threshold if key == "r2" else trial.metrics.get(key, float("inf")) <= threshold) for key, threshold in campaign.promotionThresholds.items()}}
        if campaign.mode == "real_runner":
            checks.update({
                "hard:positiveR2": trial.metrics.get("r2", float("-inf")) > 0,
                "hard:modelCardPresent": trial.modelCard is not None,
                "hard:orderedHoldout": bool(
                    trial.modelCard
                    and trial.modelCard.get("splitStrategy")
                    == "ordered_holdout_with_expanding_window_cv"
                ),
                "hard:minimumHoldoutRows": bool(
                    trial.modelCard and trial.modelCard.get("holdoutRows", 0) >= 3
                ),
            })
        if request.decision == "approved" and not all(checks.values()): raise ResearchCampaignConflictError("candidate does not satisfy promotion gates")
        now = _now(); version = f"model-{campaign.agentKey}-v{sum(1 for item in self.list(experiment_id) if item.promotion and item.promotion.status == 'approved') + 1}"
        campaign.promotion = ResearchPromotion(trialId=trial.trialId, status=request.decision, operator=request.operator.strip(),
            reason=request.reason.strip(), gateChecks=checks, promotedModelVersion=version if request.decision == "approved" else None, createdAt=now)
        campaign.status = "completed" if request.decision == "approved" else "active"
        if request.decision == "approved" and campaign.mode == "real_runner" and self.modelRegistry:
            if not trial.artifactUri or not trial.datasetFingerprint or not trial.featureNames or not trial.targetField or not trial.modelType:
                raise ResearchCampaignConflictError("real model lineage is incomplete and cannot be registered")
            self.modelRegistry.register(PromotedModelRecord(
                modelVersion=version, experimentId=experiment_id, campaignId=campaign_id, trialId=trial.trialId,
                artifactFingerprint=trial.artifactFingerprint, artifactUri=trial.artifactUri,
                datasetSnapshotId=campaign.datasetSnapshotId, datasetFingerprint=trial.datasetFingerprint,
                runnerKey=trial.runnerKey, modelType=trial.modelType, featureNames=trial.featureNames,
                targetField=trial.targetField, featureRanges=trial.featureRanges, metrics=trial.metrics,
                approvedBy=request.operator.strip(), approvalReason=request.reason.strip(), approvedAt=now,
            ))
        campaign.updatedAt = now; self.store.save(campaign); return campaign


_research_path = os.getenv("RESEARCH_CAMPAIGN_STORE_PATH", ":memory:").strip() or ":memory:"
from app.research.factory import build_research_runner
_research_runner, _research_fallback = build_research_runner()
_model_registry_path = (
    os.getenv("MODEL_REGISTRY_PATH", "data/runtime/model-registry.db").strip()
    or "data/runtime/model-registry.db"
)
promoted_model_registry = SqlitePromotedModelRegistry(project_path(_model_registry_path))
research_campaign_service = ResearchCampaignService(
    SqliteResearchCampaignStore(_research_path), _research_runner, _research_fallback,
    promoted_model_registry,
)
