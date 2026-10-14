from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from threading import RLock
from uuid import uuid4

from app.schemas.optimization import OptimizationParameters
from app.services.experiment_data_store import SqliteExperimentDataStore
from app.supplementary_design.contracts import (
    SupplementaryDesignCreate,
    SupplementaryDesignEvent,
    SupplementaryDesignReview,
    SupplementaryDesignSelection,
    SupplementaryExperimentCandidate,
    SupplementaryExperimentDesignRun,
)


class SupplementaryExperimentDesignConflictError(RuntimeError):
    pass


class SupplementaryExperimentDesignNotFoundError(LookupError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


_ALIASES = {
    "temperaturec": "temperatureC",
    "tempc": "temperatureC",
    "ph": "ph",
    "agitationrpm": "stirringRpm",
    "stirringrpm": "stirringRpm",
    "culturehours": "cultureHours",
}


def _normalized(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


class SupplementaryExperimentDesignAgent:
    def __init__(
        self,
        store: SqliteExperimentDataStore,
        evaluation_agent,
        registry,
        research_service,
        binding_service,
        inference_service,
        official_parameters_provider,
    ) -> None:
        self.store = store
        self.evaluationAgent = evaluation_agent
        self.registry = registry
        self.researchService = research_service
        self.bindingService = binding_service
        self.inferenceService = inference_service
        self.officialParametersProvider = official_parameters_provider
        self._lock = RLock()
        self._runs: dict[str, SupplementaryExperimentDesignRun] = {}
        for payload in store.list("supplementary_experiment_design"):
            run = SupplementaryExperimentDesignRun.model_validate(payload)
            self._runs[run.runId] = run

    def list(self, experiment_id: str) -> list[SupplementaryExperimentDesignRun]:
        return [
            run.model_copy(deep=True) for run in self._runs.values()
            if run.experimentId == experiment_id
        ]

    def get(
        self, experiment_id: str, run_id: str,
    ) -> SupplementaryExperimentDesignRun:
        run = self._runs.get(run_id)
        if run is None or run.experimentId != experiment_id:
            raise SupplementaryExperimentDesignNotFoundError(run_id)
        return run.model_copy(deep=True)

    def create(
        self, experiment_id: str, request: SupplementaryDesignCreate,
    ) -> SupplementaryExperimentDesignRun:
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
                raise SupplementaryExperimentDesignConflictError(
                    "commandId was reused with a different design request"
                )
            return existing.model_copy(deep=True)

        report = next(
            (
                item for item in self.evaluationAgent.list_reports(experiment_id)
                if item.reportId == request.reportId
            ),
            None,
        )
        if report is None:
            raise SupplementaryExperimentDesignNotFoundError(request.reportId)
        if report.recommendedAdmission:
            raise SupplementaryExperimentDesignConflictError(
                "model evaluation already recommends admission"
            )
        record = self.registry.latest(experiment_id)
        if record is None or record.modelVersion != report.modelVersion:
            raise SupplementaryExperimentDesignConflictError(
                "evaluation report does not belong to the current promoted model"
            )
        campaign = self.researchService.get(experiment_id, record.campaignId)
        trial = next(
            (item for item in campaign.trials if item.trialId == record.trialId),
            None,
        )
        if trial is None or trial.modelCard is None:
            raise SupplementaryExperimentDesignConflictError(
                "current model is missing an auditable model card"
            )
        binding = self.bindingService.store.latest(
            experiment_id, record.modelVersion,
        )
        defaults = self.officialParametersProvider(experiment_id) or {}
        candidates = self._generate(
            experiment_id, report, record, trial.modelCard,
            binding, defaults,
        )
        now = _now()
        run = SupplementaryExperimentDesignRun(
            runId=f"supplementary-design-{uuid4().hex[:12]}",
            experimentId=experiment_id,
            commandId=request.commandId,
            requestFingerprint=fingerprint,
            status="needsReview",
            reportId=report.reportId,
            reportInputFingerprint=report.inputFingerprint,
            reliabilityScore=report.reliabilityScore,
            modelVersion=record.modelVersion,
            modelArtifactFingerprint=record.artifactFingerprint,
            datasetFingerprint=record.datasetFingerprint,
            bindingVersion=binding.bindingVersion if binding else None,
            bindingSource="confirmed_binding" if binding else "standard_alias_fallback",
            admissionReasons=list(report.admissionReasons),
            candidates=candidates,
            events=[self._event(
                "design_created", "补实验候选已生成",
                f"基于报告 {report.reportId} 生成三套范围内主动学习方案",
            )],
            createdAt=now,
            updatedAt=now,
        )
        with self._lock:
            self._runs[run.runId] = run
            self._persist(run)
        return run.model_copy(deep=True)

    def select(
        self, experiment_id: str, run_id: str,
        request: SupplementaryDesignSelection,
    ) -> SupplementaryExperimentDesignRun:
        with self._lock:
            run = self.get(experiment_id, run_id)
            if run.status != "needsReview":
                raise SupplementaryExperimentDesignConflictError(
                    "only a design awaiting review can change selection"
                )
            available = {item.candidateId for item in run.candidates}
            selected = list(dict.fromkeys(request.candidateIds))
            if len(selected) != len(request.candidateIds) or not set(selected) <= available:
                raise SupplementaryExperimentDesignConflictError(
                    "selected candidate IDs are invalid or duplicated"
                )
            run.selectedCandidateIds = selected
            run.updatedAt = _now()
            run.events.append(self._event(
                "selection_updated", "补实验候选选择已更新",
                "、".join(selected),
            ))
            self._runs[run.runId] = run
            self._persist(run)
        return run.model_copy(deep=True)

    def review(
        self, experiment_id: str, run_id: str,
        request: SupplementaryDesignReview,
    ) -> SupplementaryExperimentDesignRun:
        with self._lock:
            run = self.get(experiment_id, run_id)
            if run.status != "needsReview":
                raise SupplementaryExperimentDesignConflictError(
                    "design is not waiting for review"
                )
            latest_model = self.registry.latest(experiment_id)
            latest_report = self.evaluationAgent.latest_report(experiment_id)
            if (
                latest_model is None
                or latest_model.modelVersion != run.modelVersion
                or latest_report is None
                or latest_report.reportId != run.reportId
                or latest_report.inputFingerprint != run.reportInputFingerprint
            ):
                raise SupplementaryExperimentDesignConflictError(
                    "current model or evaluation report changed after design generation"
                )
            if request.decision == "approved" and not run.selectedCandidateIds:
                raise SupplementaryExperimentDesignConflictError(
                    "at least one supplementary experiment candidate must be selected"
                )
            run.status = "approved" if request.decision == "approved" else "rejected"
            if request.decision == "approved":
                selected = [
                    item.model_dump(mode="json") for item in run.candidates
                    if item.candidateId in run.selectedCandidateIds
                ]
                digest = _hash({
                    "runId": run.runId,
                    "reportInputFingerprint": run.reportInputFingerprint,
                    "selected": selected,
                })
                run.planVersion = "supplement-plan-" + digest[-12:]
            run.reviewedBy = request.operator.strip()
            run.reviewReason = request.reason.strip()
            run.reviewedAt = _now()
            run.updatedAt = run.reviewedAt
            run.events.append(self._event(
                "human_review", "补实验设计人工决策已记录",
                f"{request.operator.strip()} · {request.decision} · {request.reason.strip()}",
            ))
            self._runs[run.runId] = run
            self._persist(run)
        return run.model_copy(deep=True)

    def _generate(self, experiment_id, report, record, card, binding, defaults):
        ranges = record.featureRanges
        train_stats = card["trainFeatureStats"]
        holdout_stats = card["holdoutFeatureStats"]
        drifts = {item.feature: item for item in report.driftDiagnostics}
        effects = {item.feature: item for item in report.featureEffects}

        def bounded(feature: str, value: float, margin: float = 0.05) -> float:
            allowed = ranges[feature]
            width = float(allowed.max) - float(allowed.min)
            return _clip(
                value,
                float(allowed.min) + width * margin,
                float(allowed.max) - width * margin,
            )

        residual_point = {
            feature: bounded(
                feature,
                float(holdout_stats.get(feature, train_stats[feature])["mean"]),
            )
            for feature in record.featureNames
        }
        coverage_point = {}
        for feature in record.featureNames:
            train_mean = float(train_stats[feature]["mean"])
            holdout_mean = float(holdout_stats.get(feature, train_stats[feature])["mean"])
            allowed = ranges[feature]
            direction = 1 if holdout_mean >= train_mean else -1
            edge = float(allowed.max if direction > 0 else allowed.min)
            coverage_point[feature] = bounded(
                feature, holdout_mean + 0.2 * (edge - holdout_mean), 0.1,
            )
        boundary_point = {}
        for feature in record.featureNames:
            allowed = ranges[feature]
            width = float(allowed.max) - float(allowed.min)
            effect = float(getattr(effects.get(feature), "effect", 0.0))
            boundary_point[feature] = float(allowed.min) + width * (
                0.85 if effect >= 0 else 0.15
            )

        definitions = (
            (
                "coverageRecovery", "覆盖缺口修复方案", coverage_point,
                "优先补充分布漂移与留出覆盖不足区域。",
            ),
            (
                "boundaryValidation", "重要边界验证方案", boundary_point,
                "在已观察范围内验证高重要性特征的边界响应。",
            ),
            (
                "residualCorrection", "残差区域复测方案", residual_point,
                "靠近真实留出分布中心复测，定位系统残差与偏差。",
            ),
        )
        candidates = []
        for strategy, name, feature_values, summary in definitions:
            process = self._to_process_parameters(
                feature_values, binding, defaults,
            )
            prediction = self.inferenceService.predict(
                experiment_id, feature_values,
                model_version=record.modelVersion,
                allow_extrapolation=False,
            ).prediction
            information, boundary_risk = self._scores(
                feature_values, ranges, train_stats, drifts, effects,
            )
            drift_evidence = sorted(
                report.driftDiagnostics,
                key=lambda item: (
                    item.standardizedMeanShift,
                    1 - item.holdoutRangeCoverage,
                ), reverse=True,
            )
            addresses = list(report.admissionReasons[:2]) or [
                "补充模型可靠性验证数据"
            ]
            addresses.append(
                f"重点特征 {drift_evidence[0].feature}：漂移 {drift_evidence[0].standardizedMeanShift:.3f}，覆盖率 {drift_evidence[0].holdoutRangeCoverage:.1%}"
            )
            candidates.append(SupplementaryExperimentCandidate(
                candidateId=f"supplement-candidate-{strategy}",
                strategyKey=strategy,
                displayName=name,
                summary=summary,
                modelFeatureValues={key: round(float(value), 8) for key, value in feature_values.items()},
                processParameters=process,
                exploratoryPrediction=round(float(prediction), 10),
                intervalLower=round(float(prediction) - report.predictionInterval.margin, 10),
                intervalUpper=round(float(prediction) + report.predictionInterval.margin, 10),
                intervalMethod="unreliable_model_empirical_holdout_margin",
                informationGainScore=information,
                boundaryRiskScore=boundary_risk,
                extrapolated=False,
                addressesGaps=addresses,
                evidence=[
                    f"模型 {record.modelVersion}；报告 {report.reportId}",
                    f"模型产物 {record.artifactFingerprint}",
                    "全部特征位于已注册训练范围内",
                    "探索性预测仅用于实验排序，不作为生产结果",
                ],
            ))
        return candidates

    @staticmethod
    def _scores(values, ranges, train_stats, drifts, effects):
        information_parts = []
        risks = []
        for feature, value in values.items():
            allowed = ranges[feature]
            width = max(float(allowed.max) - float(allowed.min), 1e-12)
            position = (value - float(allowed.min)) / width
            risks.append(min(1.0, abs(position - 0.5) * 2))
            std = max(abs(float(train_stats[feature].get("std", 0))), width * 0.05)
            distance = min(1.0, abs(value - float(train_stats[feature]["mean"])) / (2 * std))
            importance = float(getattr(effects.get(feature), "normalizedImportance", 0))
            drift = getattr(drifts.get(feature), "standardizedMeanShift", 0)
            drift_score = min(1.0, float(drift) / 3)
            information_parts.append(0.45 * distance + 0.35 * importance + 0.20 * drift_score)
        return (
            round(min(1.0, sum(information_parts) / len(information_parts)), 6),
            round(max(risks), 6),
        )

    @staticmethod
    def _to_process_parameters(feature_values, binding, defaults):
        parameters = {
            "temperatureC": float(defaults.get("temperatureC", 37.0)),
            "ph": float(defaults.get("ph", 6.9)),
            "cultureHours": float(defaults.get("cultureHours", 48)),
            "stirringRpm": float(defaults.get("stirringRpm", 200)),
        }
        if binding is not None:
            for entry in binding.entries:
                if entry.modelFeature in feature_values:
                    parameters[entry.simulationParameter] = (
                        float(feature_values[entry.modelFeature]) - entry.offset
                    ) / entry.scale
        else:
            for feature, value in feature_values.items():
                parameter = _ALIASES.get(_normalized(feature))
                if parameter is None:
                    raise SupplementaryExperimentDesignConflictError(
                        f"model feature {feature} has no confirmed binding or standard alias"
                    )
                parameters[parameter] = float(value)
        rounded = {
            "temperatureC": round(parameters["temperatureC"], 1),
            "ph": round(parameters["ph"], 2),
            "cultureHours": round(parameters["cultureHours"]),
            "stirringRpm": round(parameters["stirringRpm"]),
        }
        return OptimizationParameters.model_validate(rounded)

    @staticmethod
    def _event(event_type: str, title: str, detail: str) -> SupplementaryDesignEvent:
        return SupplementaryDesignEvent(
            eventId=f"supplement-event-{uuid4().hex[:10]}",
            eventType=event_type, title=title, detail=detail, createdAt=_now(),
        )

    def _persist(self, run: SupplementaryExperimentDesignRun) -> None:
        self.store.save(
            "supplementary_experiment_design", run.runId,
            run.experimentId, run.model_dump(mode="json"),
        )


from app.model_evaluation.agent import model_evaluation_agent
from app.model_registry.runtime import (
    feature_binding_service,
    promoted_model_inference_service,
)
from app.research.service import promoted_model_registry, research_campaign_service
from app.services.experiment_file_service import experiment_file_service
from app.services.experiment_service import experiment_service


supplementary_experiment_design_agent = (
    SupplementaryExperimentDesignAgent(
        store=experiment_file_service.store,
        evaluation_agent=model_evaluation_agent,
        registry=promoted_model_registry,
        research_service=research_campaign_service,
        binding_service=feature_binding_service,
        inference_service=promoted_model_inference_service,
        official_parameters_provider=experiment_service.get_official_process_parameters,
    )
    if experiment_file_service.store is not None
    else None
)
