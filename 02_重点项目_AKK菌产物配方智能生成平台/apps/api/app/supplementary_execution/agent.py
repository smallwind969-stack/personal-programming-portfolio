from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from threading import RLock
from uuid import uuid4

from app.services.experiment_data_store import SqliteExperimentDataStore
from app.supplementary_execution.contracts import (
    SupplementaryExecutionAsset,
    SupplementaryExecutionAssetAttach,
    SupplementaryExecutionBatch,
    SupplementaryExecutionBatchCreate,
    SupplementaryExecutionEvent,
    SupplementaryExecutionReview,
    SupplementaryExecutionStart,
    SupplementaryExecutionStep,
    SupplementaryExecutionStepUpdate,
)


class SupplementaryExperimentExecutionConflictError(RuntimeError):
    pass


class SupplementaryExperimentExecutionNotFoundError(LookupError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


_STEP_DEFINITIONS = (
    ("preparation", "实验准备", "确认原料、容器、批次标签与安全条件"),
    ("equipmentCheck", "设备与环境确认", "记录设备、校准状态与实验环境"),
    ("parameterExecution", "参数执行", "按冻结参数人工执行并记录偏差或异常"),
    ("sampling", "采样与重复测量", "按采样要求完成独立重复并保留原始记录"),
    ("dataArchive", "原始数据归档", "上传并关联当前实验的真实原始数据资产"),
    ("humanConfirmation", "人工完成确认", "负责人检查步骤、偏差、异常与数据完整性"),
)


class SupplementaryExperimentExecutionAgent:
    def __init__(self, store: SqliteExperimentDataStore, design_agent, registry, evaluation_agent, file_service) -> None:
        self.store = store
        self.designAgent = design_agent
        self.registry = registry
        self.evaluationAgent = evaluation_agent
        self.fileService = file_service
        self._lock = RLock()
        self._batches: dict[str, SupplementaryExecutionBatch] = {}
        for payload in store.list("supplementary_execution_batch"):
            batch = SupplementaryExecutionBatch.model_validate(payload)
            self._batches[batch.batchId] = batch

    def list(self, experiment_id: str) -> list[SupplementaryExecutionBatch]:
        with self._lock:
            return [item.model_copy(deep=True) for item in self._batches.values() if item.experimentId == experiment_id]

    def get(self, experiment_id: str, batch_id: str) -> SupplementaryExecutionBatch:
        item = self._batches.get(batch_id)
        if item is None or item.experimentId != experiment_id:
            raise SupplementaryExperimentExecutionNotFoundError(batch_id)
        return item.model_copy(deep=True)

    def create(self, experiment_id: str, request: SupplementaryExecutionBatchCreate) -> SupplementaryExecutionBatch:
        fingerprint = _hash(request.model_dump(mode="json"))
        existing_command = next((item for item in self._batches.values() if item.experimentId == experiment_id and item.commandId == request.commandId), None)
        if existing_command is not None:
            if existing_command.requestFingerprint != fingerprint:
                raise SupplementaryExperimentExecutionConflictError("commandId was reused with a different execution request")
            return existing_command.model_copy(deep=True)

        design = self.designAgent.get(experiment_id, request.designRunId)
        if design.status != "approved" or not design.planVersion:
            raise SupplementaryExperimentExecutionConflictError("only an approved supplementary plan can create an execution batch")
        if request.planVersion != design.planVersion:
            raise SupplementaryExperimentExecutionConflictError("execution request plan version does not match the approved plan")
        if request.candidateId not in design.selectedCandidateIds:
            raise SupplementaryExperimentExecutionConflictError("candidate is not selected in the approved plan")
        self._assert_current(experiment_id, design)
        duplicate = next((item for item in self._batches.values() if item.experimentId == experiment_id and item.planVersion == request.planVersion and item.candidateId == request.candidateId), None)
        if duplicate is not None:
            raise SupplementaryExperimentExecutionConflictError("approved plan candidate already has an execution batch")
        if any(item.experimentId == experiment_id and item.batchCode == request.batchCode for item in self._batches.values()):
            raise SupplementaryExperimentExecutionConflictError("batchCode is already used in this experiment")
        candidate = next((item for item in design.candidates if item.candidateId == request.candidateId), None)
        if candidate is None:
            raise SupplementaryExperimentExecutionConflictError("approved candidate snapshot is missing")
        now = _now()
        batch = SupplementaryExecutionBatch(
            batchId=f"supplement-execution-{uuid4().hex[:12]}",
            experimentId=experiment_id,
            commandId=request.commandId,
            requestFingerprint=fingerprint,
            designRunId=design.runId,
            planVersion=design.planVersion,
            candidateId=candidate.candidateId,
            strategyKey=candidate.strategyKey,
            candidateName=candidate.displayName,
            modelVersion=design.modelVersion,
            reportId=design.reportId,
            reportInputFingerprint=design.reportInputFingerprint,
            batchCode=request.batchCode,
            scale=request.scale,
            status="planned",
            plannedAt=request.plannedAt,
            replicateCount=request.replicateCount,
            samplingRequirements=request.samplingRequirements,
            frozenParameters=candidate.processParameters,
            modelFeatureValues=candidate.modelFeatureValues,
            steps=[SupplementaryExecutionStep(stepKey=key, order=index, title=title, requirement=requirement) for index, (key, title, requirement) in enumerate(_STEP_DEFINITIONS, 1)],
            createdBy=request.operator.strip(),
            createdAt=now,
            events=[self._event("batch_created", "补实验执行批次已建立", f"来自计划 {design.planVersion} 与候选 {candidate.candidateId}", request.operator)],
        )
        with self._lock:
            self._batches[batch.batchId] = batch
            self._persist(batch)
        return batch.model_copy(deep=True)

    def start(self, experiment_id: str, batch_id: str, request: SupplementaryExecutionStart) -> SupplementaryExecutionBatch:
        with self._lock:
            batch = self.get(experiment_id, batch_id)
            if batch.status != "planned":
                raise SupplementaryExperimentExecutionConflictError("only a planned execution batch can start")
            design = self.designAgent.get(experiment_id, batch.designRunId)
            self._assert_current(experiment_id, design)
            now = _now()
            batch.status = "inProgress"
            batch.startedAt = now
            batch.steps[0] = batch.steps[0].model_copy(update={"status": "inProgress", "operator": request.operator.strip(), "note": request.note.strip(), "startedAt": now})
            batch.events.append(self._event("batch_started", "补实验开始执行", request.note, request.operator))
            self._save(batch)
        return batch.model_copy(deep=True)

    def update_step(self, experiment_id: str, batch_id: str, step_key: str, request: SupplementaryExecutionStepUpdate) -> SupplementaryExecutionBatch:
        with self._lock:
            batch = self.get(experiment_id, batch_id)
            self._assert_mutable(batch)
            if batch.status not in {"inProgress", "awaitingData"}:
                raise SupplementaryExperimentExecutionConflictError("execution batch is not accepting step updates")
            index = next((index for index, step in enumerate(batch.steps) if step.stepKey == step_key), None)
            if index is None:
                raise SupplementaryExperimentExecutionNotFoundError(step_key)
            if any(step.status != "completed" for step in batch.steps[:index]):
                raise SupplementaryExperimentExecutionConflictError("previous step must be completed first")
            step = batch.steps[index]
            if step.status == "completed":
                raise SupplementaryExperimentExecutionConflictError("completed execution step is immutable")
            if step_key == "dataArchive" and request.status == "completed" and not batch.assets:
                raise SupplementaryExperimentExecutionConflictError("at least one verified real data asset is required before data archive completion")
            now = _now()
            started_at = step.startedAt or now
            batch.steps[index] = step.model_copy(update={
                "status": request.status,
                "operator": request.operator.strip(),
                "note": request.note.strip(),
                "startedAt": started_at,
                "completedAt": now if request.status == "completed" else None,
            })
            if request.status == "completed" and index + 1 < len(batch.steps):
                next_step = batch.steps[index + 1]
                batch.steps[index + 1] = next_step.model_copy(update={"status": "inProgress", "startedAt": now})
            if step_key == "sampling" and request.status == "completed":
                batch.status = "awaitingData"
            elif step_key == "dataArchive" and request.status == "completed":
                batch.status = "inProgress"
            elif step_key == "humanConfirmation" and request.status == "completed":
                batch.status = "needsReview"
            batch.events.append(self._event("step_updated", f"执行步骤：{step.title}", f"{request.status}；{request.note.strip()}", request.operator))
            self._save(batch)
        return batch.model_copy(deep=True)

    def attach_assets(self, experiment_id: str, batch_id: str, request: SupplementaryExecutionAssetAttach) -> SupplementaryExecutionBatch:
        with self._lock:
            batch = self.get(experiment_id, batch_id)
            self._assert_mutable(batch)
            if batch.status not in {"inProgress", "awaitingData"}:
                raise SupplementaryExperimentExecutionConflictError("execution batch is not accepting data assets")
            known = {item.assetId for item in batch.assets}
            additions = []
            for asset_id in request.assetIds:
                if asset_id in known:
                    continue
                asset = self.fileService.get_file_asset(experiment_id, asset_id)
                if asset is None:
                    raise SupplementaryExperimentExecutionConflictError("data asset does not belong to this experiment")
                try:
                    verified = bool(self.fileService.verify_asset_integrity(asset_id))
                except (LookupError, ValueError, OSError) as exc:
                    raise SupplementaryExperimentExecutionConflictError("data asset integrity verification failed") from exc
                if not verified:
                    raise SupplementaryExperimentExecutionConflictError("data asset integrity verification failed")
                additions.append(SupplementaryExecutionAsset(
                    assetId=asset.assetId,
                    originalName=asset.originalName,
                    contentHash=asset.contentHash,
                    parseStatus=asset.parseStatus,
                    integrityVerified=True,
                    attachedBy=request.operator.strip(),
                    attachedAt=_now(),
                    note=request.note.strip(),
                ))
            if not additions and all(asset_id in known for asset_id in request.assetIds):
                return batch.model_copy(deep=True)
            batch.assets.extend(additions)
            batch.events.append(self._event("assets_attached", "真实数据资产已关联", "、".join(item.originalName for item in additions), request.operator))
            self._save(batch)
        return batch.model_copy(deep=True)

    def review(self, experiment_id: str, batch_id: str, request: SupplementaryExecutionReview) -> SupplementaryExecutionBatch:
        with self._lock:
            batch = self.get(experiment_id, batch_id)
            if batch.status != "needsReview":
                raise SupplementaryExperimentExecutionConflictError("execution batch is not waiting for review")
            now = _now()
            batch.reviewedBy = request.operator.strip()
            batch.reviewReason = request.reason.strip()
            batch.reviewedAt = now
            if request.decision == "approved":
                if any(step.status != "completed" for step in batch.steps) or not batch.assets:
                    raise SupplementaryExperimentExecutionConflictError("all execution steps and verified data assets are required")
                batch.status = "completed"
                batch.completedAt = now
                event_type, title = "review_approved", "补实验执行记录已人工确认"
            else:
                batch.status = "inProgress"
                last = batch.steps[-1]
                batch.steps[-1] = last.model_copy(update={"status": "pending", "operator": None, "note": None, "startedAt": None, "completedAt": None})
                event_type, title = "review_rejected", "补实验执行记录已退回整改"
            batch.events.append(self._event(event_type, title, request.reason, request.operator))
            self._save(batch)
        return batch.model_copy(deep=True)

    def _assert_current(self, experiment_id: str, design) -> None:
        model = self.registry.latest(experiment_id)
        report = self.evaluationAgent.latest_report(experiment_id)
        if model is None or model.modelVersion != design.modelVersion or report is None or report.reportId != design.reportId or report.inputFingerprint != design.reportInputFingerprint:
            raise SupplementaryExperimentExecutionConflictError("approved supplementary plan is stale because model or report changed")

    @staticmethod
    def _assert_mutable(batch: SupplementaryExecutionBatch) -> None:
        if batch.status in {"completed", "cancelled"}:
            raise SupplementaryExperimentExecutionConflictError("terminal execution batch is immutable")

    @staticmethod
    def _event(event_type: str, title: str, detail: str, operator: str) -> SupplementaryExecutionEvent:
        return SupplementaryExecutionEvent(eventId=f"supplement-execution-event-{uuid4().hex[:10]}", eventType=event_type, title=title, detail=detail.strip(), operator=operator.strip(), createdAt=_now())

    def _save(self, batch: SupplementaryExecutionBatch) -> None:
        self._batches[batch.batchId] = batch
        self._persist(batch)

    def _persist(self, batch: SupplementaryExecutionBatch) -> None:
        self.store.save("supplementary_execution_batch", batch.batchId, batch.experimentId, batch.model_dump(mode="json"))


from app.model_evaluation.agent import model_evaluation_agent
from app.research.service import promoted_model_registry
from app.services.experiment_file_service import experiment_file_service
from app.supplementary_design.agent import supplementary_experiment_design_agent


supplementary_experiment_execution_agent = (
    SupplementaryExperimentExecutionAgent(
        store=experiment_file_service.store,
        design_agent=supplementary_experiment_design_agent,
        registry=promoted_model_registry,
        evaluation_agent=model_evaluation_agent,
        file_service=experiment_file_service,
    )
    if experiment_file_service.store is not None and supplementary_experiment_design_agent is not None
    else None
)
