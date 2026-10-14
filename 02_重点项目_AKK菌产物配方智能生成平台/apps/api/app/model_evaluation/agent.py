from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from threading import RLock
from uuid import uuid4

import numpy as np

from app.model_evaluation.contracts import (
    FeatureDriftDiagnostic,
    ModelEvaluationReport,
    ModelFeatureEffect,
    PredictionIntervalEvidence,
    ResidualDiagnostics,
)
from app.model_registry.store import SqlitePromotedModelRegistry
from app.research.artifacts import ContentAddressedModelArtifactStore
from app.research.service import ResearchCampaignService
from app.services.experiment_data_store import SqliteExperimentDataStore
from app.services.experiment_file_service import experiment_file_service
from app.services.experiment_service import ExperimentService, experiment_service


def _hash(payload: object) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _clip(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class ModelEvaluationAgent:
    def __init__(
        self,
        registry: SqlitePromotedModelRegistry,
        research_service: ResearchCampaignService,
        artifacts: ContentAddressedModelArtifactStore,
        workspace_service: ExperimentService,
        store: SqliteExperimentDataStore | None,
    ) -> None:
        self.registry = registry
        self.researchService = research_service
        self.artifacts = artifacts
        self.workspaceService = workspace_service
        self.store = store
        self._reports: dict[str, list[ModelEvaluationReport]] = {}
        self._lock = RLock()
        if store is not None:
            for payload in store.list("model_evaluation_report"):
                report = ModelEvaluationReport.model_validate(payload)
                self._reports.setdefault(report.experimentId, []).append(report)
            for reports in self._reports.values():
                reports.sort(key=lambda item: item.reportVersion)

    def _context(self, experiment_id: str):
        record = self.registry.latest(experiment_id)
        if record is None or record.status != "approved":
            raise ValueError("an approved promoted model is required for evaluation")
        campaign = self.researchService.get(experiment_id, record.campaignId)
        trial = next(
            (item for item in campaign.trials if item.trialId == record.trialId),
            None,
        )
        if trial is None or trial.modelCard is None:
            raise ValueError("promoted model is missing its auditable model card")
        card = trial.modelCard
        if (
            trial.artifactFingerprint != record.artifactFingerprint
            or trial.datasetFingerprint != record.datasetFingerprint
            or card.get("datasetFingerprint") != record.datasetFingerprint
        ):
            raise ValueError("model evaluation lineage does not match promoted model")
        return record, campaign, trial, card

    def current_input_fingerprint(self, experiment_id: str) -> str:
        record, _, trial, card = self._context(experiment_id)
        return _hash({
            "model": record.model_dump(mode="json"),
            "trialId": trial.trialId,
            "modelCard": card,
        })

    def create_report(self, experiment_id: str) -> ModelEvaluationReport:
        record, campaign, trial, card = self._context(experiment_id)
        artifact_verified = self.artifacts.verify(record.artifactFingerprint)
        residual = ResidualDiagnostics.model_validate(card["residualDiagnostics"])
        observations = card["holdoutObservations"]
        absolute_residuals = np.asarray(
            [abs(float(item["residual"])) for item in observations], dtype=float,
        )
        margin = float(np.quantile(absolute_residuals, 0.95, method="higher"))
        empirical_coverage = float(np.mean(absolute_residuals <= margin))
        interval = PredictionIntervalEvidence(
            method="empirical_holdout_absolute_error",
            confidenceLevel=0.95,
            margin=round(margin, 10),
            empiricalCoverage=round(empirical_coverage, 6),
            sampleCount=len(observations),
            calibrated=False,
            limitation=(
                "区间由同一留出集的绝对残差估计，尚未使用独立校准集；"
                "仅用于研发风险提示。"
            ),
        )

        drifts: list[FeatureDriftDiagnostic] = []
        for feature in record.featureNames:
            train = card["trainFeatureStats"][feature]
            holdout = card["holdoutFeatureStats"][feature]
            denominator = max(abs(float(train["std"])), 1e-12)
            shift = abs(float(holdout["mean"]) - float(train["mean"])) / denominator
            coverage = float(card["holdoutRangeCoverage"][feature])
            severity = (
                "high" if shift > 2.5 or coverage < 0.5
                else "medium" if shift > 1.5 or coverage < 0.8
                else "low"
            )
            drifts.append(FeatureDriftDiagnostic(
                feature=feature,
                standardizedMeanShift=round(shift, 6),
                holdoutRangeCoverage=round(coverage, 6),
                severity=severity,
                trainMean=float(train["mean"]),
                holdoutMean=float(holdout["mean"]),
            ))

        effects = [
            ModelFeatureEffect.model_validate(item)
            for item in card["featureEffects"]
        ]
        r2 = float(trial.metrics.get("r2", -1))
        cv_std_r2 = abs(float(card["crossValidationStd"].get("r2", 1)))
        max_shift = max(item.standardizedMeanShift for item in drifts)
        average_coverage = sum(item.holdoutRangeCoverage for item in drifts) / len(drifts)
        target_std = max(float(card["targetRange"].get("std", 0)), 1e-12)
        bias_ratio = abs(residual.meanResidual) / target_std
        train_rows = int(card["trainRows"])
        holdout_rows = int(card["holdoutRows"])
        score_breakdown = {
            "predictivePerformance": _clip(r2),
            "crossValidationStability": _clip(1 - cv_std_r2 / 0.25),
            "distributionStability": _clip(1 - max_shift / 2.5),
            "rangeCoverage": _clip(average_coverage),
            "residualBias": _clip(1 - bias_ratio),
            "dataAdequacy": _clip(min(train_rows / 50, holdout_rows / 10)),
        }
        score = round(
            0.30 * score_breakdown["predictivePerformance"]
            + 0.15 * score_breakdown["crossValidationStability"]
            + 0.15 * score_breakdown["distributionStability"]
            + 0.15 * score_breakdown["rangeCoverage"]
            + 0.10 * score_breakdown["residualBias"]
            + 0.15 * score_breakdown["dataAdequacy"],
            6,
        )

        reasons: list[str] = []
        if not artifact_verified:
            reasons.append("模型产物完整性校验失败")
        if r2 < 0.5:
            reasons.append(f"留出集 R²={r2:.3f}，低于仿真准入下限 0.500")
        if cv_std_r2 > 0.25:
            reasons.append("交叉验证波动过大")
        if max_shift > 2.5:
            reasons.append("留出数据相对训练数据发生高强度分布漂移")
        if average_coverage < 0.8:
            reasons.append("留出数据落在训练特征范围内的平均覆盖率不足 80%")
        if abs(residual.lag1Autocorrelation) > 0.8:
            reasons.append("残差存在明显时序自相关")
        if train_rows < 20 or holdout_rows < 5:
            reasons.append("训练或留出样本量不足")
        if score < 0.7:
            reasons.append(f"综合可靠性评分 {score:.3f} 低于准入线 0.700")
        recommended = not reasons
        grade = "high" if score >= 0.85 else "medium" if score >= 0.7 else "low"
        report = ModelEvaluationReport(
            reportId=f"model-eval-{uuid4().hex[:12]}",
            experimentId=experiment_id,
            reportVersion=len(self._reports.get(experiment_id, [])) + 1,
            status="needsReview",
            modelVersion=record.modelVersion,
            campaignId=campaign.campaignId,
            trialId=trial.trialId,
            modelType=record.modelType,
            artifactFingerprint=record.artifactFingerprint,
            artifactVerified=artifact_verified,
            datasetSnapshotId=record.datasetSnapshotId,
            datasetFingerprint=record.datasetFingerprint,
            inputFingerprint=self.current_input_fingerprint(experiment_id),
            performanceMetrics=trial.metrics,
            residualDiagnostics=residual,
            predictionInterval=interval,
            driftDiagnostics=drifts,
            featureEffects=effects,
            scoreBreakdown={
                key: round(value, 6) for key, value in score_breakdown.items()
            },
            reliabilityScore=score,
            reliabilityGrade=grade,
            recommendedAdmission=recommended,
            admissionAllowed=False,
            admissionReasons=reasons or [
                "自动可靠性检查通过，等待研发人员确认适用边界"
            ],
            createdAt=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._reports.setdefault(experiment_id, []).append(report)
            self._persist(report)
        return report.model_copy(deep=True)

    def _persist(self, report: ModelEvaluationReport) -> None:
        if self.store is not None:
            self.store.save(
                "model_evaluation_report", report.reportId,
                report.experimentId, report.model_dump(mode="json"),
            )

    def list_reports(self, experiment_id: str) -> list[ModelEvaluationReport]:
        with self._lock:
            return [
                report.model_copy(deep=True)
                for report in self._reports.get(experiment_id, [])
            ]

    def latest_report(self, experiment_id: str) -> ModelEvaluationReport | None:
        reports = self.list_reports(experiment_id)
        return reports[-1] if reports else None

    def review(
        self, experiment_id: str, report_id: str, decision: str,
        operator: str, reason: str,
    ) -> ModelEvaluationReport:
        if not operator.strip() or len(reason.strip()) < 2:
            raise ValueError("model evaluation review requires operator and reason")
        with self._lock:
            reports = self._reports.get(experiment_id, [])
            index = next(
                (position for position, item in enumerate(reports)
                 if item.reportId == report_id),
                None,
            )
            if index is None:
                raise LookupError("model evaluation report was not found")
            report = reports[index]
            if report.status != "needsReview":
                raise ValueError("only a report needing review can be decided")
            if report.inputFingerprint != self.current_input_fingerprint(experiment_id):
                raise ValueError("model evaluation report input fingerprint is stale")
            if decision == "approved" and not report.recommendedAdmission:
                raise ValueError("model evaluation does not recommend simulation admission")
            if decision not in {"approved", "rejected"}:
                raise ValueError("unsupported model evaluation review decision")
            updated = report.model_copy(update={
                "status": "confirmed" if decision == "approved" else "rejected",
                "admissionAllowed": decision == "approved",
                "reviewedBy": operator.strip(),
                "reviewReason": reason.strip(),
                "reviewedAt": datetime.now(timezone.utc).isoformat(),
            })
            reports[index] = updated
            self._persist(updated)
        if decision == "approved":
            self.workspaceService.apply_model_evaluation(updated, report.modelType)
        return updated.model_copy(deep=True)

    def assert_simulation_ready(self, experiment_id: str) -> ModelEvaluationReport:
        reports = [
            item for item in self.list_reports(experiment_id)
            if item.status == "confirmed" and item.admissionAllowed
        ]
        if not reports:
            raise ValueError(
                "model evaluation human confirmation is required before simulation"
            )
        report = reports[-1]
        if report.inputFingerprint != self.current_input_fingerprint(experiment_id):
            raise ValueError("confirmed model evaluation report is stale")
        return report


from app.research.service import promoted_model_registry, research_campaign_service
import os

model_evaluation_agent = ModelEvaluationAgent(
    promoted_model_registry,
    research_campaign_service,
    ContentAddressedModelArtifactStore(
        os.getenv("RESEARCH_ARTIFACT_PATH", "data/runtime/model-artifacts")
    ),
    experiment_service,
    experiment_file_service.store,
)
