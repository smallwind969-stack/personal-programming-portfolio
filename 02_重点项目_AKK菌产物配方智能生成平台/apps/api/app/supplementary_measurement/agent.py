from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from threading import RLock
from uuid import uuid4

from app.services.experiment_data_store import SqliteExperimentDataStore
from app.supplementary_measurement.contracts import (
    SupplementaryMeasurement,
    SupplementaryMeasurementBatch,
    SupplementaryMeasurementBatchCreate,
    SupplementaryMeasurementEvent,
    SupplementaryMeasurementQualityGate,
    SupplementaryMeasurementReview,
    SupplementaryMeasurementSubmission,
)


class SupplementaryMeasurementHandoffConflictError(RuntimeError):
    pass


class SupplementaryMeasurementHandoffNotFoundError(LookupError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


class SupplementaryMeasurementHandoffAgent:
    PARAMETER_TOLERANCES = {
        "temperatureC": 0.2, "ph": 0.05, "cultureHours": 1.0, "stirringRpm": 5.0,
    }

    def __init__(self, store: SqliteExperimentDataStore, execution_agent, registry) -> None:
        self.store = store
        self.executionAgent = execution_agent
        self.registry = registry
        self._lock = RLock()
        self._batches: dict[str, SupplementaryMeasurementBatch] = {}
        for payload in store.list("supplementary_measurement_batch"):
            batch = SupplementaryMeasurementBatch.model_validate(payload)
            self._batches[batch.measurementBatchId] = batch

    def list(self, experiment_id: str) -> list[SupplementaryMeasurementBatch]:
        with self._lock:
            return [item.model_copy(deep=True) for item in self._batches.values() if item.experimentId == experiment_id]

    def get(self, experiment_id: str, batch_id: str) -> SupplementaryMeasurementBatch:
        item = self._batches.get(batch_id)
        if item is None or item.experimentId != experiment_id:
            raise SupplementaryMeasurementHandoffNotFoundError(batch_id)
        return item.model_copy(deep=True)

    def create(self, experiment_id: str, request: SupplementaryMeasurementBatchCreate) -> SupplementaryMeasurementBatch:
        fingerprint = _hash(request.model_dump(mode="json"))
        command = next((item for item in self._batches.values() if item.experimentId == experiment_id and item.commandId == request.commandId), None)
        if command is not None:
            if command.requestFingerprint != fingerprint:
                raise SupplementaryMeasurementHandoffConflictError("commandId was reused with a different measurement handoff request")
            return command.model_copy(deep=True)
        execution = self.executionAgent.get(experiment_id, request.executionBatchId)
        if execution.status != "completed":
            raise SupplementaryMeasurementHandoffConflictError("only a completed supplementary execution batch can create a measurement handoff")
        duplicate = next((item for item in self._batches.values() if item.experimentId == experiment_id and item.executionBatchId == execution.batchId), None)
        if duplicate is not None:
            raise SupplementaryMeasurementHandoffConflictError("execution batch already has a measurement handoff")
        if not execution.assets or any(not item.integrityVerified for item in execution.assets):
            raise SupplementaryMeasurementHandoffConflictError("completed execution has no verified source assets")
        model = self.registry.get(experiment_id, execution.modelVersion)
        if model is None or not model.targetField:
            raise SupplementaryMeasurementHandoffConflictError("parent model target contract was not found")
        now = _now()
        batch = SupplementaryMeasurementBatch(
            measurementBatchId=f"supplement-measurement-{uuid4().hex[:12]}",
            experimentId=experiment_id,
            commandId=request.commandId,
            requestFingerprint=fingerprint,
            executionBatchId=execution.batchId,
            planVersion=execution.planVersion,
            candidateId=execution.candidateId,
            executionBatchCode=execution.batchCode,
            parentModelVersion=execution.modelVersion,
            reportId=execution.reportId,
            targetMetric=model.targetField,
            status="draft",
            frozenParameters=execution.frozenParameters,
            allowedSourceAssetIds=[item.assetId for item in execution.assets],
            sourceAssetNames={item.assetId: item.originalName for item in execution.assets},
            createdBy=request.operator.strip(),
            createdAt=now,
            events=[self._event("handoff_created", "真实测量录入任务已建立", f"来自执行批次 {execution.batchId}", request.operator)],
        )
        with self._lock:
            self._batches[batch.measurementBatchId] = batch
            self._persist(batch)
        return batch.model_copy(deep=True)

    def submit(self, experiment_id: str, batch_id: str, request: SupplementaryMeasurementSubmission) -> SupplementaryMeasurementBatch:
        with self._lock:
            batch = self.get(experiment_id, batch_id)
            if batch.status != "draft":
                raise SupplementaryMeasurementHandoffConflictError("only a draft measurement handoff can receive measurements")
            source_ids = {item.sourceAssetId for item in request.measurements}
            if not source_ids or not source_ids <= set(batch.allowedSourceAssetIds):
                raise SupplementaryMeasurementHandoffConflictError("measurement source asset is not verified in the execution batch")
            measurements = [SupplementaryMeasurement(measurementId=f"supplement-measurement-value-{uuid4().hex[:10]}", **item.model_dump(mode="json")) for item in request.measurements]
            wrong_target = [item.metricName for item in measurements if item.isModelTarget and _normalized(item.metricName) != _normalized(batch.targetMetric)]
            if wrong_target:
                raise SupplementaryMeasurementHandoffConflictError("model target measurement does not match parent model target")
            now = _now()
            batch.status = "needsReview"
            batch.actualParameters = request.actualParameters
            batch.measurements = measurements
            batch.contaminationObserved = request.contaminationObserved
            batch.equipmentAbnormalities = [item.strip() for item in request.equipmentAbnormalities if item.strip()]
            batch.notes = request.notes.strip()
            batch.submittedAt = now
            batch.qualityGate = self._evaluate(batch, human_confirmed=False)
            batch.events.append(self._event("measurements_submitted", "真实测量已提交质量检查", f"共 {len(measurements)} 条测量", batch.createdBy))
            self._save(batch)
        return batch.model_copy(deep=True)

    def review(self, experiment_id: str, batch_id: str, request: SupplementaryMeasurementReview) -> SupplementaryMeasurementBatch:
        with self._lock:
            batch = self.get(experiment_id, batch_id)
            if batch.status != "needsReview" or batch.qualityGate is None:
                raise SupplementaryMeasurementHandoffConflictError("measurement handoff is not waiting for review")
            technical = {key: value for key, value in batch.qualityGate.checks.items() if key != "humanConfirmed"}
            if request.decision == "approved" and not all(technical.values()):
                raise SupplementaryMeasurementHandoffConflictError("measurement quality gate has not passed")
            now = _now()
            batch.reviewedBy = request.operator.strip()
            batch.reviewReason = request.reason.strip()
            batch.reviewedAt = now
            if request.decision == "approved":
                version = "feedback-dataset-" + _hash({
                    "measurementBatchId": batch.measurementBatchId,
                    "measurements": [item.model_dump(mode="json") for item in batch.measurements],
                    "actualParameters": batch.actualParameters.model_dump(mode="json"),
                })[-12:]
                batch.status = "confirmed"
                batch.qualityGate = self._evaluate(batch, human_confirmed=True, dataset_version=version)
                self._persist_feedback_dataset(batch)
                event_type, title = "measurement_confirmed", "真实测量反馈资产已确认"
            else:
                batch.status = "rejected"
                event_type, title = "measurement_rejected", "真实测量任务已驳回"
            batch.events.append(self._event(event_type, title, request.reason, request.operator))
            self._save(batch)
        return batch.model_copy(deep=True)

    def _evaluate(self, batch: SupplementaryMeasurementBatch, human_confirmed: bool, dataset_version: str | None = None) -> SupplementaryMeasurementQualityGate:
        targets = [item for item in batch.measurements if item.isModelTarget and _normalized(item.metricName) == _normalized(batch.targetMetric)]
        source_ids = {item.sourceAssetId for item in batch.measurements}
        target_replicates = [item.replicate for item in targets]
        parameter_match = batch.actualParameters is not None and all(
            abs(getattr(batch.actualParameters, key) - getattr(batch.frozenParameters, key)) <= tolerance + 1e-9
            for key, tolerance in self.PARAMETER_TOLERANCES.items()
        )
        checks = {
            "executionCompleted": self.executionAgent.get(batch.experimentId, batch.executionBatchId).status == "completed",
            "sourceAssetsVerified": bool(source_ids) and source_ids <= set(batch.allowedSourceAssetIds),
            "actualParametersWithinTolerance": parameter_match,
            "targetMetricMatchesModel": bool(targets),
            "minimumTargetReplicates": len(targets) >= 3,
            "uniqueTargetReplicates": len(target_replicates) == len(set(target_replicates)),
            "targetUnitsConsistent": len({item.unit for item in targets}) == 1,
            "measurementMethodsPresent": all(item.method.strip() for item in batch.measurements),
            "noContamination": not batch.contaminationObserved,
            "noEquipmentAbnormalities": not batch.equipmentAbnormalities,
            "humanConfirmed": human_confirmed,
        }
        labels = {
            "executionCompleted": "来源补实验执行批次尚未完成",
            "sourceAssetsVerified": "测量缺少执行批次中已验证的来源文件",
            "actualParametersWithinTolerance": "实际参数超出冻结工艺容差",
            "targetMetricMatchesModel": "模型目标指标不匹配或缺失",
            "minimumTargetReplicates": "模型目标独立重复少于 3 次",
            "uniqueTargetReplicates": "模型目标重复编号不唯一",
            "targetUnitsConsistent": "模型目标测量单位不一致",
            "measurementMethodsPresent": "测量方法记录不完整",
            "noContamination": "批次观察到污染",
            "noEquipmentAbnormalities": "批次存在设备异常",
            "humanConfirmed": "等待研发人员人工确认",
        }
        return SupplementaryMeasurementQualityGate(
            eligible=all(checks.values()), checks=checks,
            reasons=[labels[key] for key, passed in checks.items() if not passed],
            targetMetric=batch.targetMetric, targetReplicateCount=len(targets),
            feedbackDatasetVersion=dataset_version if all(checks.values()) else None,
            checkedAt=_now(),
        )

    def _persist_feedback_dataset(self, batch: SupplementaryMeasurementBatch) -> None:
        gate = batch.qualityGate
        if gate is None or not gate.eligible or gate.feedbackDatasetVersion is None or batch.actualParameters is None:
            return
        targets = [item for item in batch.measurements if item.isModelTarget and _normalized(item.metricName) == _normalized(batch.targetMetric)]
        payload = {
            "feedbackDatasetVersion": gate.feedbackDatasetVersion,
            "experimentId": batch.experimentId,
            "sourceType": "supplementary_measurement",
            "supplementaryMeasurementBatchId": batch.measurementBatchId,
            "executionBatchId": batch.executionBatchId,
            "parentModelVersion": batch.parentModelVersion,
            "planVersion": batch.planVersion,
            "rows": [{
                **batch.actualParameters.model_dump(mode="json"),
                batch.targetMetric: sum(item.value for item in targets) / len(targets),
                "replicateCount": len(targets),
                "batchCode": batch.executionBatchCode,
            }],
            "measurementIds": [item.measurementId for item in batch.measurements],
            "sourceAssetIds": sorted({item.sourceAssetId for item in batch.measurements}),
            "createdAt": _now(),
        }
        self.store.save("experimental_feedback_dataset", gate.feedbackDatasetVersion, batch.experimentId, payload)

    @staticmethod
    def _event(event_type: str, title: str, detail: str, operator: str) -> SupplementaryMeasurementEvent:
        return SupplementaryMeasurementEvent(eventId=f"supplement-measurement-event-{uuid4().hex[:10]}", eventType=event_type, title=title, detail=detail.strip(), operator=operator.strip(), createdAt=_now())

    def _save(self, batch: SupplementaryMeasurementBatch) -> None:
        self._batches[batch.measurementBatchId] = batch
        self._persist(batch)

    def _persist(self, batch: SupplementaryMeasurementBatch) -> None:
        self.store.save("supplementary_measurement_batch", batch.measurementBatchId, batch.experimentId, batch.model_dump(mode="json"))


from app.research.service import promoted_model_registry
from app.services.experiment_file_service import experiment_file_service
from app.supplementary_execution.agent import supplementary_experiment_execution_agent


supplementary_measurement_handoff_agent = (
    SupplementaryMeasurementHandoffAgent(
        store=experiment_file_service.store,
        execution_agent=supplementary_experiment_execution_agent,
        registry=promoted_model_registry,
    )
    if experiment_file_service.store is not None and supplementary_experiment_execution_agent is not None
    else None
)
