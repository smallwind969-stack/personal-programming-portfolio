from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from threading import RLock
from uuid import uuid4

from app.experimental_feedback.contracts import (
    ExperimentalFeedbackReview,
    ExperimentalMeasurement,
    ExperimentalValidationBatch,
    ExperimentalValidationBatchCreate,
    ExperimentalValidationSubmission,
    RetrainingEligibilityGate,
)
from app.services.experiment_data_store import SqliteExperimentDataStore
from app.services.experiment_file_service import experiment_file_service
from app.services.experiment_service import experiment_service
from app.services.optimization_orchestrator import optimization_orchestrator


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


class ExperimentalFeedbackConflictError(RuntimeError):
    pass


class ExperimentalFeedbackNotFoundError(LookupError):
    pass


class ExperimentalFeedbackAgent:
    """Turns observed validation batches into reviewed, retraining-eligible assets."""

    PARAMETER_TOLERANCES = {
        "temperatureC": 0.2, "ph": 0.05, "cultureHours": 1.0,
        "stirringRpm": 5.0,
    }

    def __init__(self, store: SqliteExperimentDataStore | None) -> None:
        self.store = store
        self._items: dict[str, list[ExperimentalValidationBatch]] = {}
        self._lock = RLock()
        if store is not None:
            for payload in store.list("experimental_validation_batch"):
                item = ExperimentalValidationBatch.model_validate(payload)
                self._items.setdefault(item.experimentId, []).append(item)
            for items in self._items.values():
                items.sort(key=lambda item: item.createdAt)

    def list(self, experiment_id: str) -> list[ExperimentalValidationBatch]:
        with self._lock:
            return [item.model_copy(deep=True) for item in self._items.get(experiment_id, [])]

    def get(self, experiment_id: str, validation_batch_id: str) -> ExperimentalValidationBatch:
        item = next(
            (item for item in self._items.get(experiment_id, [])
             if item.validationBatchId == validation_batch_id), None,
        )
        if item is None:
            raise ExperimentalFeedbackNotFoundError(validation_batch_id)
        return item

    def create(self, experiment_id: str, request: ExperimentalValidationBatchCreate) -> ExperimentalValidationBatch:
        run = optimization_orchestrator.get_run(experiment_id, request.optimizationRunId)
        if run.status != "completed" or run.officialParameterVersion is None:
            raise ExperimentalFeedbackConflictError("only an approved optimization run can create a validation batch")
        if (
            request.parameterVersion != run.officialParameterVersion
            or request.predictedResultVersion != run.newResultVersion
        ):
            raise ExperimentalFeedbackConflictError("validation batch lineage does not match the approved optimization result")
        if run.submittedParameters is None or run.baseSimulationRunId is None:
            raise ExperimentalFeedbackConflictError("approved optimization lineage is incomplete")
        existing = next(
            (item for item in self._items.get(experiment_id, [])
             if item.batchCode == request.batchCode), None,
        )
        if existing:
            if existing.optimizationRunId != request.optimizationRunId:
                raise ExperimentalFeedbackConflictError("batchCode is already linked to another optimization run")
            return existing.model_copy(deep=True)
        item = ExperimentalValidationBatch(
            validationBatchId=f"validation-batch-{uuid4().hex[:12]}",
            experimentId=experiment_id,
            optimizationRunId=run.runId,
            parameterVersion=request.parameterVersion,
            predictedResultVersion=request.predictedResultVersion,
            parentModelVersion=run.baseModelVersion,
            parentSimulationRunId=run.baseSimulationRunId,
            batchCode=request.batchCode,
            scale=request.scale,
            status="draft",
            plannedAt=request.plannedAt,
            approvedParameters=run.submittedParameters,
            createdBy=request.operator.strip(), createdAt=_now(),
        )
        with self._lock:
            self._items.setdefault(experiment_id, []).append(item)
            self._persist(item)
        return item.model_copy(deep=True)

    def submit(
        self, experiment_id: str, validation_batch_id: str,
        request: ExperimentalValidationSubmission,
    ) -> ExperimentalValidationBatch:
        with self._lock:
            item = self.get(experiment_id, validation_batch_id)
            if item.status != "draft":
                raise ExperimentalFeedbackConflictError("only a draft validation batch can receive measurements")
            run = optimization_orchestrator.get_run(experiment_id, item.optimizationRunId)
            target_names = self._target_names(experiment_id, run)
            measurements = [ExperimentalMeasurement(
                measurementId=f"measurement-{uuid4().hex[:10]}", **entry.model_dump(),
            ) for entry in request.measurements]
            for measurement in measurements:
                if measurement.isModelTarget and measurement.metricName not in target_names:
                    raise ExperimentalFeedbackConflictError(
                        f"model target measurement {measurement.metricName} does not match approved model lineage"
                    )
            updated = item.model_copy(update={
                "actualParameters": request.actualParameters,
                "measurements": measurements,
                "contaminationObserved": request.contaminationObserved,
                "equipmentAbnormalities": request.equipmentAbnormalities,
                "notes": request.notes,
                "status": "needsReview",
                "submittedAt": _now(),
            })
            updated.qualityGate = self._evaluate(updated, target_names, confirmed=False)
            self._replace(updated); self._persist(updated)
        return updated.model_copy(deep=True)

    def review(
        self, experiment_id: str, validation_batch_id: str,
        request: ExperimentalFeedbackReview,
    ) -> ExperimentalValidationBatch:
        with self._lock:
            item = self.get(experiment_id, validation_batch_id)
            if item.status != "needsReview" or item.qualityGate is None:
                raise ExperimentalFeedbackConflictError("validation batch is not waiting for review")
            pre_review_checks = {
                key: passed
                for key, passed in item.qualityGate.checks.items()
                if key != "humanConfirmed"
            }
            if request.decision == "approved" and not all(pre_review_checks.values()):
                raise ExperimentalFeedbackConflictError("feedback quality gate has not passed")
            status = "confirmed" if request.decision == "approved" else "rejected"
            updated = item.model_copy(update={
                "status": status, "reviewedBy": request.operator.strip(),
                "reviewReason": request.reason.strip(), "reviewedAt": _now(),
            })
            if status == "confirmed":
                target_names = {
                    measurement.metricName for measurement in updated.measurements
                    if measurement.isModelTarget
                }
                dataset_version = "feedback-dataset-" + _hash({
                    "batch": updated.model_dump(mode="json"),
                    "targets": sorted(target_names),
                }).removeprefix("sha256:")[:12]
                updated.qualityGate = self._evaluate(
                    updated, target_names, confirmed=True,
                    dataset_version=dataset_version,
                )
                self._persist_feedback_dataset(updated)
                experiment_service.apply_confirmed_experimental_feedback(updated)
            self._replace(updated); self._persist(updated)
        return updated.model_copy(deep=True)

    def _evaluate(
        self, item: ExperimentalValidationBatch, target_names: set[str],
        confirmed: bool, dataset_version: str | None = None,
    ) -> RetrainingEligibilityGate:
        target_measurements = [
            measurement for measurement in item.measurements
            if measurement.isModelTarget and measurement.metricName in target_names
        ]
        target_units = {measurement.unit for measurement in target_measurements}
        parameter_match = bool(item.actualParameters) and all(
            abs(getattr(item.actualParameters, key) - getattr(item.approvedParameters, key)) <= tolerance + 1e-9
            for key, tolerance in self.PARAMETER_TOLERANCES.items()
        )
        checks = {
            "lineageComplete": bool(item.parentModelVersion and item.parentSimulationRunId),
            "actualParametersWithinTolerance": parameter_match,
            "minimumTargetReplicates": len(target_measurements) >= 3,
            "targetUnitsConsistent": len(target_units) == 1,
            "measurementMethodsPresent": all(measurement.method.strip() for measurement in item.measurements),
            "noContamination": not item.contaminationObserved,
            "noEquipmentAbnormalities": not item.equipmentAbnormalities,
            "humanConfirmed": confirmed,
        }
        labels = {
            "lineageComplete": "优化、模型和仿真血缘不完整",
            "actualParametersWithinTolerance": "实际执行参数偏离批准参数容差",
            "minimumTargetReplicates": "模型目标有效重复测量少于 3 次",
            "targetUnitsConsistent": "模型目标测量单位不一致或缺失",
            "measurementMethodsPresent": "测量方法证据不完整",
            "noContamination": "批次观察到污染",
            "noEquipmentAbnormalities": "批次存在设备异常",
            "humanConfirmed": "等待研发人员人工确认",
        }
        reasons = [labels[key] for key, passed in checks.items() if not passed]
        return RetrainingEligibilityGate(
            eligible=all(checks.values()), checks=checks, reasons=reasons,
            targetMetric=next(iter(sorted(target_names)), "unavailable"),
            targetReplicateCount=len(target_measurements),
            feedbackDatasetVersion=dataset_version if all(checks.values()) else None,
            checkedAt=_now(),
        )

    def _target_names(self, experiment_id: str, run) -> set[str]:
        targets = {evidence.targetField for evidence in run.submittedModelEvidence}
        if targets:
            return targets
        overview = experiment_service.get_workspace_overview(experiment_id)
        return set(overview.targetMetrics) if overview is not None else set()

    def _persist_feedback_dataset(self, item: ExperimentalValidationBatch) -> None:
        if self.store is None or item.qualityGate is None or not item.qualityGate.eligible:
            return
        target_values = [
            measurement.value for measurement in item.measurements
            if measurement.isModelTarget
        ]
        payload = {
            "feedbackDatasetVersion": item.qualityGate.feedbackDatasetVersion,
            "experimentId": item.experimentId,
            "validationBatchId": item.validationBatchId,
            "parentModelVersion": item.parentModelVersion,
            "parameterVersion": item.parameterVersion,
            "rows": [{
                **item.actualParameters.model_dump(mode="json"),
                item.qualityGate.targetMetric: sum(target_values) / len(target_values),
                "replicateCount": len(target_values),
                "batchCode": item.batchCode,
            }],
            "measurementIds": [measurement.measurementId for measurement in item.measurements],
            "createdAt": _now(),
        }
        self.store.save(
            "experimental_feedback_dataset", item.qualityGate.feedbackDatasetVersion,
            item.experimentId, payload,
        )

    def _replace(self, updated: ExperimentalValidationBatch) -> None:
        items = self._items.get(updated.experimentId, [])
        index = next(i for i, item in enumerate(items) if item.validationBatchId == updated.validationBatchId)
        items[index] = updated

    def _persist(self, item: ExperimentalValidationBatch) -> None:
        if self.store is not None:
            self.store.save(
                "experimental_validation_batch", item.validationBatchId,
                item.experimentId, item.model_dump(mode="json"),
            )


experimental_feedback_agent = ExperimentalFeedbackAgent(experiment_file_service.store)
