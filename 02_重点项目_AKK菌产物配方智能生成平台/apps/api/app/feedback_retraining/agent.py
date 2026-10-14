from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from threading import RLock
from uuid import uuid4

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from app.feedback_retraining.contracts import (
    FeedbackModelCandidate,
    FeedbackPromotionGate,
    FeedbackRetrainingCreate,
    FeedbackRetrainingEvent,
    FeedbackRetrainingReview,
    FeedbackRetrainingRun,
    FeedbackRetrainingStage,
)
from app.feedback_retraining.dataset import FeedbackDerivedDatasetBuilder
from app.research.contracts import (
    ResearchCampaignCreate,
    ResearchPromotionRequest,
    ResearchTrialCreate,
)
from app.services.experiment_data_store import SqliteExperimentDataStore


class FeedbackRetrainingConflictError(RuntimeError):
    pass


class FeedbackRetrainingNotFoundError(LookupError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


_STAGES = (
    ("feedback-dataset", "datasetAssembly", "反馈数据装配", "锁定历史数据、真实反馈和特征目标契约。"),
    ("incumbent-evaluation", "incumbentEvaluation", "现役模型外部评估", "在未见过的真实反馈留出批次上评估现役模型。"),
    ("candidate-training", "candidateTraining", "候选模型重训练", "使用固定预算训练三种候选算法并保存模型产物。"),
    ("candidate-comparison", "candidateComparison", "新旧模型对比", "在同一外部留出集上比较指标并计算硬门禁。"),
    ("human-review", "humanReview", "人工晋升复核", "研发负责人决定是否晋升候选模型。"),
)


class FeedbackRetrainingAgent:
    def __init__(
        self,
        store: SqliteExperimentDataStore,
        dataset_builder,
        registry,
        research_service,
        artifact_store,
        model_evaluation,
        incumbent_evaluator=None,
    ) -> None:
        self.store = store
        self.datasetBuilder = dataset_builder
        self.registry = registry
        self.researchService = research_service
        self.artifacts = artifact_store
        self.modelEvaluation = model_evaluation
        self.incumbentEvaluator = incumbent_evaluator or self._evaluate_incumbent
        self._lock = RLock()
        self._runs: dict[str, FeedbackRetrainingRun] = {}
        for payload in store.list("feedback_retraining_run"):
            run = FeedbackRetrainingRun.model_validate(payload)
            self._runs[run.runId] = run

    def list(self, experiment_id: str) -> list[FeedbackRetrainingRun]:
        return [
            run.model_copy(deep=True)
            for run in self._runs.values()
            if run.experimentId == experiment_id
        ]

    def get(self, experiment_id: str, run_id: str) -> FeedbackRetrainingRun:
        run = self._runs.get(run_id)
        if run is None or run.experimentId != experiment_id:
            raise FeedbackRetrainingNotFoundError(run_id)
        return run.model_copy(deep=True)

    def create(
        self, experiment_id: str, request: FeedbackRetrainingCreate,
    ) -> FeedbackRetrainingRun:
        fingerprint = _hash(request.model_dump(mode="json"))
        existing = next(
            (
                run for run in self._runs.values()
                if run.experimentId == experiment_id
                and run.commandId == request.commandId
            ),
            None,
        )
        if existing is not None:
            if existing.requestFingerprint != fingerprint:
                raise FeedbackRetrainingConflictError(
                    "commandId was reused with a different retraining request"
                )
            return existing.model_copy(deep=True)
        latest = self.registry.latest(experiment_id)
        if latest is None or latest.modelVersion != request.parentModelVersion:
            raise FeedbackRetrainingConflictError(
                "parent model is not the current promoted model"
            )
        if len(set(request.feedbackDatasetVersions)) < 3:
            raise FeedbackRetrainingConflictError(
                "at least three independent feedback datasets are required"
            )
        dataset = self.datasetBuilder.build(
            experiment_id, request.parentModelVersion,
            request.feedbackDatasetVersions,
        )
        if dataset.externalHoldoutRowCount < 3:
            raise FeedbackRetrainingConflictError(
                "at least three independent feedback holdout rows are required"
            )
        now = _now()
        stages = [
            FeedbackRetrainingStage(
                stageId=stage_id, stageKey=key, stageName=name,
                status="completed" if index == 0 else "running" if index == 1 else "waiting",
                progressPercent=100 if index == 0 else 10 if index == 1 else 0,
                detail=detail,
                outputSummary=(
                    [
                        f"派生数据集 {dataset.datasetId}",
                        f"历史 {dataset.historicalRowCount} 行；外部留出 {dataset.externalHoldoutRowCount} 行",
                    ] if index == 0 else []
                ),
                startedAt=now if index <= 1 else None,
                completedAt=now if index == 0 else None,
            )
            for index, (stage_id, key, name, detail) in enumerate(_STAGES)
        ]
        run = FeedbackRetrainingRun(
            runId=f"feedback-retraining-{uuid4().hex[:12]}",
            experimentId=experiment_id,
            commandId=request.commandId,
            requestFingerprint=fingerprint,
            status="running",
            parentModelVersion=request.parentModelVersion,
            feedbackDatasetVersions=list(request.feedbackDatasetVersions),
            fixedBudgetSeconds=request.fixedBudgetSeconds,
            derivedDatasetId=dataset.datasetId,
            derivedDatasetFingerprint=dataset.datasetFingerprint,
            historicalRowCount=dataset.historicalRowCount,
            trainingFeedbackRowCount=dataset.trainingFeedbackRowCount,
            externalHoldoutRowCount=dataset.externalHoldoutRowCount,
            stages=stages,
            currentStageId="incumbent-evaluation",
            progressPercent=20,
            events=[self._event(
                "dataset_assembled", "反馈派生数据集已锁定",
                f"{dataset.datasetId} · {dataset.datasetFingerprint}",
            )],
            createdAt=now,
            updatedAt=now,
        )
        with self._lock:
            self._runs[run.runId] = run
            self._persist(run)
        return run.model_copy(deep=True)

    def advance(self, experiment_id: str, run_id: str) -> FeedbackRetrainingRun:
        with self._lock:
            run = self.get(experiment_id, run_id)
            if run.status != "running":
                raise FeedbackRetrainingConflictError(
                    "only a running retraining activity can advance"
                )
            if run.currentStageId == "incumbent-evaluation":
                parent = self.registry.get(experiment_id, run.parentModelVersion)
                if parent is None:
                    raise FeedbackRetrainingConflictError("parent model artifact lineage is missing")
                dataset = self.datasetBuilder.get(experiment_id, run.derivedDatasetId)
                metrics = self.incumbentEvaluator(parent, dataset)
                run.incumbentMetrics = {key: float(value) for key, value in metrics.items()}
                self._complete_and_start(run, 1, 2, [
                    f"R² {metrics['r2']:.4f}", f"MAE {metrics['mae']:.4f}",
                    f"RMSE {metrics['rmse']:.4f}",
                ])
                run.events.append(self._event(
                    "incumbent_evaluated", "现役模型外部评估已完成",
                    f"父模型 {run.parentModelVersion} 使用 {run.externalHoldoutRowCount} 个独立反馈批次",
                ))
            elif run.currentStageId == "candidate-training":
                campaign = self.researchService.create(
                    experiment_id,
                    ResearchCampaignCreate(
                        commandId=run.commandId + ":campaign",
                        datasetSnapshotId=run.derivedDatasetId,
                        agentKey="modeling",
                        baselineMetrics=run.incumbentMetrics,
                        primaryMetric="r2", direction="maximize",
                        fixedBudgetSeconds=run.fixedBudgetSeconds,
                        # The freshly retrained default estimator is itself a candidate.
                        # Improvement is therefore gated against the incumbent below,
                        # not against that candidate baseline.
                        minimumImprovement=0.0,
                        promotionThresholds={"r2": 0.5, "mae": max(run.incumbentMetrics["mae"] * 1.05, 1e-9)},
                    ),
                )
                algorithms = (
                    ("ridge", {"algorithm": "ridge", "alpha": 1.0}),
                    ("random_forest", {"algorithm": "random_forest", "nEstimators": 160, "maxDepth": 5}),
                    ("gradient_boosting", {"algorithm": "gradient_boosting", "nEstimators": 120, "learningRate": 0.03, "maxDepth": 2}),
                )
                trials = [
                    self.researchService.run_trial(
                        experiment_id, campaign.campaignId,
                        ResearchTrialCreate(
                            commandId=f"{run.commandId}:{algorithm}",
                            hypothesis=f"使用 {algorithm} 在真实反馈外部留出集上比较泛化能力",
                            parameterPatch=patch,
                        ),
                    )
                    for algorithm, patch in algorithms
                ]
                run.researchCampaignId = campaign.campaignId
                run.candidates = [
                    self._candidate(trial, run.incumbentMetrics)
                    for trial in trials
                ]
                refreshed = self.researchService.get(experiment_id, campaign.campaignId)
                run.championTrialId = refreshed.bestTrialId
                self._complete_and_start(
                    run, 2, 3,
                    [f"完成 {len(trials)} 个候选训练", f"当前最佳 {run.championTrialId}"],
                )
                run.events.append(self._event(
                    "candidates_trained", "候选模型训练已完成",
                    "Ridge、RandomForest、GradientBoosting 已使用同一外部留出集评估",
                ))
            elif run.currentStageId == "candidate-comparison":
                run.promotionGate = self._gate(run)
                stage = run.stages[3]
                stage.status = "completed"
                stage.progressPercent = 100
                stage.completedAt = _now()
                stage.outputSummary = [
                    f"技术门禁 {'通过' if run.promotionGate.eligible else '未通过'}",
                    f"候选 {run.championTrialId}",
                ]
                review = run.stages[4]
                review.status = "needsReview"
                review.progressPercent = 0
                review.startedAt = _now()
                run.currentStageId = "human-review"
                run.status = "needsReview"
                run.progressPercent = 90
                run.events.append(self._event(
                    "comparison_completed", "新旧模型对比已完成",
                    "等待研发负责人决定是否晋升",
                ))
            else:
                raise FeedbackRetrainingConflictError("retraining activity cannot advance")
            run.updatedAt = _now()
            self._runs[run.runId] = run
            self._persist(run)
        return run.model_copy(deep=True)

    def review(
        self, experiment_id: str, run_id: str,
        request: FeedbackRetrainingReview,
    ) -> FeedbackRetrainingRun:
        with self._lock:
            run = self.get(experiment_id, run_id)
            if run.status != "needsReview" or run.promotionGate is None:
                raise FeedbackRetrainingConflictError(
                    "retraining activity is not waiting for review"
                )
            latest = self.registry.latest(experiment_id)
            if latest is None or latest.modelVersion != run.parentModelVersion:
                raise FeedbackRetrainingConflictError(
                    "current promoted model changed after retraining started"
                )
            if request.decision == "approved" and not run.promotionGate.eligible:
                raise FeedbackRetrainingConflictError(
                    "candidate does not satisfy retraining promotion gates"
                )
            if request.decision == "approved":
                campaign = self.researchService.promote(
                    experiment_id, run.researchCampaignId,
                    ResearchPromotionRequest(
                        trialId=run.championTrialId,
                        decision="approved", operator=request.operator,
                        reason=request.reason,
                    ),
                )
                run.promotedModelVersion = campaign.promotion.promotedModelVersion
                report = self.modelEvaluation.create_report(experiment_id)
                run.evaluationReportId = report.reportId
                run.status = "completed"
            else:
                run.status = "rejected"
            run.reviewedBy = request.operator.strip()
            run.reviewReason = request.reason.strip()
            run.reviewedAt = _now()
            review_stage = run.stages[4]
            review_stage.status = "completed"
            review_stage.progressPercent = 100
            review_stage.completedAt = run.reviewedAt
            review_stage.outputSummary = [
                f"决策：{request.decision}", f"操作人：{request.operator.strip()}",
            ]
            run.currentStageId = None
            run.progressPercent = 100
            run.updatedAt = run.reviewedAt
            run.events.append(self._event(
                "human_review", "人工晋升决策已记录",
                f"{request.operator.strip()} · {request.decision} · {request.reason.strip()}",
            ))
            self._runs[run.runId] = run
            self._persist(run)
        return run.model_copy(deep=True)

    def _gate(self, run: FeedbackRetrainingRun) -> FeedbackPromotionGate:
        campaign = self.researchService.get(
            run.experimentId, run.researchCampaignId,
        )
        champion = next(
            trial for trial in campaign.trials
            if trial.trialId == run.championTrialId
        )
        artifact_verified = False
        try:
            artifact_verified = bool(self.artifacts.verify(champion.artifactFingerprint))
        except ValueError:
            artifact_verified = False
        incumbent = run.incumbentMetrics
        checks = {
            "independentFeedbackHoldout": run.externalHoldoutRowCount >= 3,
            "candidateIsCampaignBest": champion.trialId == campaign.bestTrialId,
            "minimumImprovement": champion.deltaFromBaseline >= campaign.minimumImprovement,
            "r2Threshold": champion.metrics.get("r2", -math.inf) >= campaign.promotionThresholds.get("r2", -math.inf),
            "maeThreshold": champion.metrics.get("mae", math.inf) <= campaign.promotionThresholds.get("mae", math.inf),
            "improvesIncumbentR2": champion.metrics.get("r2", -math.inf) > incumbent.get("r2", -math.inf),
            "maeNotRegressed": champion.metrics.get("mae", math.inf) <= incumbent.get("mae", math.inf) * 1.05,
            "rmseNotRegressed": champion.metrics.get("rmse", math.inf) <= incumbent.get("rmse", math.inf) * 1.05,
            "artifactVerified": artifact_verified,
        }
        labels = {
            "independentFeedbackHoldout": "独立真实反馈留出批次少于 3 个",
            "candidateIsCampaignBest": "候选不是当前研究活动最佳试验",
            "minimumImprovement": "候选未达到最小改进幅度",
            "r2Threshold": "候选 R² 未达到阈值",
            "maeThreshold": "候选 MAE 未达到阈值",
            "improvesIncumbentR2": "候选 R² 未优于现役模型同集表现",
            "maeNotRegressed": "候选 MAE 相对现役模型显著退化",
            "rmseNotRegressed": "候选 RMSE 相对现役模型显著退化",
            "artifactVerified": "候选模型产物完整性校验失败",
        }
        return FeedbackPromotionGate(
            eligible=all(checks.values()), checks=checks,
            reasons=[labels[key] for key, passed in checks.items() if not passed],
            checkedAt=_now(),
        )

    def _evaluate_incumbent(self, parent, dataset) -> dict[str, float]:
        numeric = self.datasetBuilder.load_numeric(
            dataset.experimentId, dataset.datasetId,
        )
        split = numeric.holdoutStartIndex
        if split is None or len(numeric.y) - split < 3:
            raise FeedbackRetrainingConflictError(
                "incumbent comparison requires at least three external holdout rows"
            )
        bundle = self.artifacts.load_verified(
            parent.artifactFingerprint, parent.artifactUri,
        )
        if list(bundle.get("featureNames", [])) != list(numeric.featureNames):
            raise FeedbackRetrainingConflictError(
                "incumbent artifact feature contract does not match derived dataset"
            )
        prediction = bundle["model"].predict(numeric.X[split:])
        actual = numeric.y[split:]
        return {
            "mae": round(float(mean_absolute_error(actual, prediction)), 10),
            "rmse": round(float(mean_squared_error(actual, prediction) ** 0.5), 10),
            "r2": round(float(r2_score(actual, prediction)), 10),
        }

    def _candidate(self, trial, incumbent: dict[str, float]) -> FeedbackModelCandidate:
        metrics = {key: float(value) for key, value in trial.metrics.items()}
        artifact_verified = False
        try:
            artifact_verified = bool(self.artifacts.verify(trial.artifactFingerprint))
        except ValueError:
            artifact_verified = False
        return FeedbackModelCandidate(
            trialId=trial.trialId,
            algorithm=str(getattr(trial, "modelType", None) or trial.trialId),
            modelType=getattr(trial, "modelType", None),
            metrics=metrics,
            deltaFromIncumbent={
                key: round(value - incumbent.get(key, 0.0), 10)
                for key, value in metrics.items()
            },
            artifactFingerprint=trial.artifactFingerprint,
            artifactVerified=artifact_verified,
        )

    @staticmethod
    def _complete_and_start(
        run: FeedbackRetrainingRun, current_index: int,
        next_index: int, outputs: list[str],
    ) -> None:
        now = _now()
        current = run.stages[current_index]
        current.status = "completed"
        current.progressPercent = 100
        current.completedAt = now
        current.outputSummary = outputs
        next_stage = run.stages[next_index]
        next_stage.status = "running"
        next_stage.progressPercent = 10
        next_stage.startedAt = now
        run.currentStageId = next_stage.stageId
        run.progressPercent = 20 * (next_index + 1)

    @staticmethod
    def _event(event_type: str, title: str, detail: str) -> FeedbackRetrainingEvent:
        return FeedbackRetrainingEvent(
            eventId=f"feedback-retrain-event-{uuid4().hex[:10]}",
            eventType=event_type, title=title, detail=detail, createdAt=_now(),
        )

    def _persist(self, run: FeedbackRetrainingRun) -> None:
        self.store.save(
            "feedback_retraining_run", run.runId,
            run.experimentId, run.model_dump(mode="json"),
        )


from app.model_evaluation.agent import model_evaluation_agent
from app.research.artifacts import ContentAddressedModelArtifactStore
from app.research.service import promoted_model_registry, research_campaign_service
from app.services.experiment_file_service import experiment_file_service
from app.services.feature_engineering_agent import feature_engineering_agent
import os


feedback_retraining_agent = (
    FeedbackRetrainingAgent(
        store=experiment_file_service.store,
        dataset_builder=FeedbackDerivedDatasetBuilder(
            experiment_file_service.store,
            feature_engineering_agent.export_numeric_training_dataset,
            promoted_model_registry,
        ),
        registry=promoted_model_registry,
        research_service=research_campaign_service,
        artifact_store=ContentAddressedModelArtifactStore(
            os.getenv("RESEARCH_ARTIFACT_PATH", "data/runtime/model-artifacts")
        ),
        model_evaluation=model_evaluation_agent,
    )
    if experiment_file_service.store is not None
    else None
)
