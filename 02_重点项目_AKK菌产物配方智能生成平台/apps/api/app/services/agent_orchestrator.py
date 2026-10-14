from __future__ import annotations

from datetime import datetime, timezone
from functools import wraps
from threading import RLock
from uuid import uuid4

from app.agent_runtime.contracts import AgentRuntimeAdapter, RuntimeCommand, RuntimeConflictError, RuntimeContext, RuntimeGraphDefinition, RuntimeNodeDefinition, RuntimeNotFoundError, RuntimeSnapshot
from app.agent_runtime.deterministic import DeterministicRuntimeAdapter
from app.agent_runtime.factory import build_runtime_adapter
from app.services.schema_recognition_agent import schema_recognition_agent
from app.services.result_interpretation_agent import result_interpretation_agent
from app.agent_registry.builtin import agent_catalog

from app.schemas.experiments import (
    AgentGuidancePreview,
    AgentRunEvent,
    AgentRunNode,
    ExperimentAgentRun,
    HumanDecision,
)


# The catalog is authoritative. The tuple projection preserves the existing UI model
# while LangGraph topology and presentation metadata come from versioned manifests.
_DATA_WORKFLOW = agent_catalog.workflow("experiment-data-analysis")
NODE_TEMPLATES = tuple(
    (
        node.nodeId, node.agentKey, agent_catalog.agent(node.agentKey).displayName, node.stageLabel,
        node.inputSummary, node.methodSummary, node.metricSummary, node.outputSummary,
    )
    for node in _DATA_WORKFLOW.nodes
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def synchronized(method):
    @wraps(method)
    def guarded(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return guarded


class AgentRunConflictError(RuntimeError):
    pass


class AgentRunNotFoundError(LookupError):
    pass


class AgentOrchestrator:
    """Deterministic v1 state-graph facade, replaceable by LangGraph later."""

    def __init__(self, runtime: AgentRuntimeAdapter | None = None, runtime_backend: str = "deterministic") -> None:
        self._runs: dict[str, ExperimentAgentRun] = {}
        self._run_ids_by_experiment: dict[str, list[str]] = {}
        self._guidance: dict[str, AgentGuidancePreview] = {}
        self._runtime: AgentRuntimeAdapter = runtime or DeterministicRuntimeAdapter()
        self._runtime_backend = runtime_backend
        self._lock = RLock()
        self.refresh_recovered_runs()

    @staticmethod
    def _graph_definition() -> RuntimeGraphDefinition:
        workflow = agent_catalog.workflow("experiment-data-analysis")
        return RuntimeGraphDefinition(
            graphId=f"{workflow.workflowKey}-v{workflow.version}",
            nodes=[RuntimeNodeDefinition(nodeId=node.nodeId, displayName=node.stageLabel, handlerKey=node.agentKey, requiresHuman=node.requiresHuman) for node in workflow.nodes],
            edges={source: targets[0] for source, targets in workflow.edges.items() if targets},
            entryNodeId=workflow.entryNodeId,
        )

    @synchronized
    def create_run(self, experiment_id: str, parent_run_id: str | None = None, initial_guidance: AgentGuidancePreview | None = None) -> ExperimentAgentRun:
        run_ids = self._run_ids_by_experiment.setdefault(experiment_id, [])
        version = len(run_ids) + 1
        now = _now()
        run_id = f"agent-run-{uuid4().hex[:10]}"
        runtime_snapshot = self._runtime.start(
            self._graph_definition(),
            {
                "experimentId": experiment_id,
                "version": version,
                "businessRunId": run_id,
                "parentRunId": parent_run_id,
                "businessCreatedAt": now,
                "nodeResults": {item[0]: {"summary": list(item[7]), "evidenceRefs": [f"experiment://{experiment_id}/{item[0]}"], "confidenceScore": 1.0 if item[1] == "humanReview" else 0.82, "riskItems": [], "validationItems": []} for item in NODE_TEMPLATES},
                "activeGuidance": initial_guidance.model_dump() if initial_guidance else None,
            },
            RuntimeContext(experimentId=experiment_id),
        )
        nodes = [
            AgentRunNode(
                nodeId=node_id,
                agentKey=agent_key,
                agentName=agent_name,
                stageLabel=stage_label,
                status="running" if index == 0 else "waiting",
                progressPercent=15 if index == 0 else 0,
                inputSummary=inputs,
                methodSummary=methods,
                metricSummary=metrics,
                outputSummary=[] if index > 0 else outputs,
                startedAt=now if index == 0 else None,
            )
            for index, (node_id, agent_key, agent_name, stage_label, inputs, methods, metrics, outputs) in enumerate(NODE_TEMPLATES)
        ]
        run = ExperimentAgentRun(
            runId=run_id,
            runtimeBackend=self._runtime_backend,
            runtimeRunId=runtime_snapshot.runId,
            runtimeRevision=runtime_snapshot.revision,
            parentRunId=parent_run_id,
            experimentId=experiment_id,
            version=version,
            status="running",
            currentNodeId=nodes[0].nodeId,
            progressPercent=8,
            nodes=nodes,
            events=[self._event("runStarted", None, "流程运行已开始", f"创建执行版本 v{version}，进入数据收集定位节点。")],
            createdAt=now,
            updatedAt=now,
            disclaimer="当前为确定性研发流程演示，输出仅作为研发实验建议。",
        )
        if initial_guidance:
            run.appliedGuidance.append(initial_guidance)
        self._runs[run_id] = run
        run_ids.append(run_id)
        return self._project(run, runtime_snapshot)

    def latest_run(self, experiment_id: str) -> ExperimentAgentRun:
        run_ids = self._run_ids_by_experiment.get(experiment_id, [])
        return self.get_run(experiment_id, run_ids[-1]) if run_ids else self.create_run(experiment_id)

    def peek_latest_run(self, experiment_id: str) -> ExperimentAgentRun | None:
        """Return an existing run without creating a demo run as a read side effect."""
        run_ids = self._run_ids_by_experiment.get(experiment_id, [])
        return self.get_run(experiment_id, run_ids[-1]) if run_ids else None

    def get_run(self, experiment_id: str, run_id: str) -> ExperimentAgentRun:
        self.refresh_recovered_runs()
        run = self._runs.get(run_id)
        if run is None or run.experimentId != experiment_id:
            raise AgentRunNotFoundError(run_id)
        try:
            snapshot = self._runtime.get(run.runtimeRunId)
        except RuntimeNotFoundError as exc:
            raise AgentRunNotFoundError(run.runtimeRunId) from exc
        if snapshot.experimentId != experiment_id:
            raise AgentRunConflictError("Runtime belongs to another experiment")
        return self._project(run, snapshot)

    def refresh_recovered_runs(self) -> None:
        if not self._runtime_backend.endswith("-sqlite"):
            return
        refresher = getattr(self._runtime, "refresh_all", None)
        if refresher:
            refresher()
        snapshots = self._runtime.list_snapshots()
        with self._lock:
            for snapshot in snapshots:
                business_run_id = snapshot.state.get("businessRunId")
                if not business_run_id or business_run_id in self._runs:
                    continue
                version = int(snapshot.state.get("version", 1))
                created_at = str(snapshot.state.get("businessCreatedAt") or snapshot.events[0].createdAt)
                nodes = [
                    AgentRunNode(
                        nodeId=node_id, agentKey=agent_key, agentName=agent_name, stageLabel=stage_label,
                        status="waiting", progressPercent=0, inputSummary=inputs, methodSummary=methods,
                        metricSummary=metrics, outputSummary=[],
                    )
                    for node_id, agent_key, agent_name, stage_label, inputs, methods, metrics, _ in NODE_TEMPLATES
                ]
                run = ExperimentAgentRun(
                    runId=business_run_id, runtimeBackend=self._runtime_backend, runtimeRunId=snapshot.runId,
                    runtimeRevision=snapshot.revision, parentRunId=snapshot.state.get("parentRunId"),
                    experimentId=snapshot.experimentId, version=version, status=snapshot.status,
                    currentNodeId=snapshot.currentNodeId, progressPercent=0, nodes=nodes, events=[],
                    createdAt=created_at, updatedAt=created_at,
                    disclaimer="当前为研发流程演示，所有输出仅作为研发实验建议。",
                )
                self._runs[business_run_id] = self._project(run, snapshot)
                ids = self._run_ids_by_experiment.setdefault(snapshot.experimentId, [])
                if business_run_id not in ids:
                    ids.append(business_run_id)
                    ids.sort(key=lambda item: self._runs[item].version)

    @synchronized
    def advance(self, experiment_id: str, run_id: str, expected_revision: int, command_id: str) -> ExperimentAgentRun:
        with self._lock:
            run = self.get_run(experiment_id, run_id)
            try:
                current_snapshot = self._runtime.get(run.runtimeRunId)
                next_node_id = self._graph_definition().edges.get(current_snapshot.currentNodeId or "")
                checkpoint = next((item[0] for item in NODE_TEMPLATES if run.pendingGuidance and item[1] == run.pendingGuidance.safeCheckpoint), None)
                applying_guidance = run.pendingGuidance if checkpoint == next_node_id else None
                state_patch = {"activeGuidance": applying_guidance.model_dump(), "pendingGuidance": None} if applying_guidance else {}
                if current_snapshot.currentNodeId == "schema-recognition":
                    recognition = schema_recognition_agent.create_run(experiment_id, f"schema-node-{run.runId}")
                    state_patch["schemaRecognition"] = {
                        "runId": recognition.runId, "mode": recognition.mode,
                        "candidateCount": recognition.candidateCount,
                        "reviewCount": recognition.reviewCount,
                        "conflictCount": recognition.conflictCount,
                    }
                if current_snapshot.currentNodeId == "model-evaluation":
                    interpretation = result_interpretation_agent.create_run(experiment_id, f"result-interpretation-{run.runId}")
                    state_patch["resultInterpretation"] = {
                        "runId": interpretation.runId, "mode": interpretation.mode,
                        "sourceTaskId": interpretation.sourceTaskId,
                        "confidenceLevel": interpretation.confidenceLevel,
                        "suggestionCount": len(interpretation.nextExperimentSuggestions),
                    }
                snapshot = self._runtime.advance(run.runtimeRunId, RuntimeCommand(
                    command="advance", commandId=command_id, expectedRevision=expected_revision,
                    statePatch=state_patch,
                    patchEventType="guidanceApplied" if applying_guidance else None,
                    patchDetail=applying_guidance.intentSummary if applying_guidance else None,
                ))
            except (RuntimeConflictError, RuntimeNotFoundError) as exc:
                raise AgentRunConflictError(str(exc)) from exc
            if applying_guidance:
                applying_guidance.status = "applied"
                run.appliedGuidance.append(applying_guidance)
                run.pendingGuidance = None
            run.updatedAt = _now()
            return self._project(run, snapshot)

    @synchronized
    def stop(self, experiment_id: str, run_id: str, expected_revision: int | None = None, command_id: str | None = None) -> ExperimentAgentRun:
        with self._lock:
            run = self.get_run(experiment_id, run_id)
            try:
                snapshot = self._runtime.advance(run.runtimeRunId, RuntimeCommand(
                    command="stop", expectedRevision=expected_revision or run.runtimeRevision,
                    commandId=command_id or f"stop-{uuid4().hex[:10]}",
                ))
            except (RuntimeConflictError, RuntimeNotFoundError) as exc:
                raise AgentRunConflictError(str(exc)) from exc
            run.updatedAt = _now()
            return self._project(run, snapshot)

    @synchronized
    def restart(self, experiment_id: str, run_id: str, guidance_id: str | None = None) -> ExperimentAgentRun:
        previous = self.get_run(experiment_id, run_id)
        if previous.status != "stopped":
            raise AgentRunConflictError("Only a stopped run can be restarted")
        guidance = None
        if guidance_id:
            guidance = self._guidance.get(guidance_id)
            if guidance is None:
                raise AgentRunNotFoundError(guidance_id)
            self._assert_guidance_owner(guidance, experiment_id, run_id)
            if guidance.status != "preview" or not guidance.requiresRestart:
                raise AgentRunConflictError("Guidance is not an unapplied restart plan")
        applied_guidance = guidance.model_copy(update={"status": "applied"}) if guidance else None
        child = self.create_run(experiment_id, parent_run_id=run_id, initial_guidance=applied_guidance)
        if guidance:
            guidance.status = "applied"
        return child

    @synchronized
    def preview_guidance(self, experiment_id: str, run_id: str, prompt: str) -> AgentGuidancePreview:
        run = self.get_run(experiment_id, run_id)
        if run.status not in {"running", "needsReview"}:
            raise AgentRunConflictError(f"Run in {run.status} state cannot accept guidance")
        modeling_change = any(token in prompt.lower() for token in ("模型", "训练", "特征", "xgboost", "lstm"))
        guidance = AgentGuidancePreview(
            guidanceId=f"guidance-{uuid4().hex[:10]}",
            experimentId=experiment_id,
            runId=run_id,
            prompt=prompt,
            intentSummary=f"将用户要求转成可审计规则：{prompt.strip()}",
            affectedNodes=["featureEngineering", "modeling", "modelEvaluation"] if modeling_change else ["schemaRecognition", "cleaningAlignment"],
            planChanges=["在节点输入中增加企业规则", "保留原配置用于结果对比", "在事件时间线记录人工指令"],
            comparisonImpact="模型或特征变更会影响跨版本可比性。" if modeling_change else "字段规则变更仅在后续安全检查点生效。",
            safeCheckpoint="featureEngineering" if modeling_change else "schemaRecognition",
            requiresRestart=modeling_change,
            status="preview",
        )
        self._guidance[guidance.guidanceId] = guidance
        return guidance

    @synchronized
    def apply_guidance(self, experiment_id: str, run_id: str, guidance_id: str, confirmed: bool) -> ExperimentAgentRun:
        run = self.get_run(experiment_id, run_id)
        snapshot = self._runtime.get(run.runtimeRunId)
        guidance = self._guidance.get(guidance_id)
        if guidance is None:
            raise AgentRunNotFoundError(guidance_id)
        self._assert_guidance_owner(guidance, experiment_id, run_id)
        if guidance.status != "preview":
            raise AgentRunConflictError(f"Guidance in {guidance.status} state cannot be applied again")
        if run.status not in {"running", "needsReview"}:
            raise AgentRunConflictError(f"Run in {run.status} state cannot accept guidance")
        if run.pendingGuidance and run.pendingGuidance.guidanceId != guidance_id:
            raise AgentRunConflictError("Another guidance is already scheduled for this run")
        if not confirmed:
            try:
                snapshot = self._runtime.patch_state(run.runtimeRunId, {}, "guidanceRejected", guidance.intentSummary, snapshot.revision, f"guidance-{guidance_id}-reject")
            except (RuntimeConflictError, RuntimeNotFoundError) as exc:
                raise AgentRunConflictError(str(exc)) from exc
            guidance.status = "rejected"
        elif guidance.requiresRestart:
            raise AgentRunConflictError("This guidance changes completed/modeling configuration and requires restart")
        else:
            current_index = next(i for i, node in enumerate(run.nodes) if node.nodeId == run.currentNodeId)
            safe_index = next(i for i, node in enumerate(run.nodes) if node.agentKey == guidance.safeCheckpoint)
            if current_index > safe_index:
                raise AgentRunConflictError("The safe checkpoint has passed; stop and restart to apply this guidance")
            if current_index == safe_index:
                try:
                    snapshot = self._runtime.patch_state(run.runtimeRunId, {"activeGuidance": guidance.model_dump(), "pendingGuidance": None}, "guidanceApplied", guidance.intentSummary, snapshot.revision, f"guidance-{guidance_id}-apply")
                except (RuntimeConflictError, RuntimeNotFoundError) as exc:
                    raise AgentRunConflictError(str(exc)) from exc
                guidance.status = "applied"
                run.appliedGuidance.append(guidance)
            else:
                try:
                    snapshot = self._runtime.patch_state(run.runtimeRunId, {"pendingGuidance": guidance.model_dump()}, "guidanceScheduled", guidance.intentSummary, snapshot.revision, f"guidance-{guidance_id}-schedule")
                except (RuntimeConflictError, RuntimeNotFoundError) as exc:
                    raise AgentRunConflictError(str(exc)) from exc
                guidance.status = "scheduled"
                run.pendingGuidance = guidance
        run.updatedAt = _now()
        return self._project(run, snapshot)

    @synchronized
    def review(
        self,
        experiment_id: str,
        run_id: str,
        decision: str,
        reason: str,
        operator: str,
        impact_scope: list[str],
    ) -> ExperimentAgentRun:
        run = self.get_run(experiment_id, run_id)
        if run.status != "needsReview" or run.currentNodeId != "human-review":
            raise AgentRunConflictError("Run is not waiting for a human review decision")
        try:
            runtime_snapshot = self._runtime.resume(run.runtimeRunId, {"decision": decision, "operator": operator, "reason": reason})
        except (RuntimeConflictError, RuntimeNotFoundError) as exc:
            raise AgentRunConflictError(str(exc)) from exc
        now = _now()
        record = HumanDecision(
            decisionId=f"decision-{uuid4().hex[:10]}",
            decision=decision,
            reason=reason,
            operator=operator,
            impactScope=impact_scope,
            createdAt=now,
        )
        run.humanDecisions.append(record)
        node = next(node for node in run.nodes if node.nodeId == "human-review")
        node.status = "completed" if decision == "approved" else "stopped"
        node.progressPercent = 100
        node.completedAt = now
        node.outputSummary = [f"决策：{decision}", f"操作人：{operator}", f"理由：{reason}"]
        run.status = "completed" if decision == "approved" else "stopped"
        run.currentNodeId = None
        run.progressPercent = 100 if decision == "approved" else run.progressPercent
        run.updatedAt = now
        run.events.append(self._event("humanDecisionRecorded", "human-review", "人工验收决策已记录", f"{operator}：{reason}"))
        return self._project(run, runtime_snapshot)

    def _project(self, run: ExperimentAgentRun, snapshot: RuntimeSnapshot) -> ExperimentAgentRun:
        """Pure execution projection: RuntimeSnapshot is the only mutable state source."""
        if snapshot.runId != run.runtimeRunId or snapshot.experimentId != run.experimentId:
            raise AgentRunConflictError("Runtime ownership mismatch")
        runtime_nodes = {node.nodeId: node for node in snapshot.nodes}
        started_at: dict[str, str] = {}
        completed_at: dict[str, str] = {}
        for event in snapshot.events:
            if event.nodeId and event.eventType in {"runStarted", "nodeStarted", "humanReviewRequired"}:
                started_at.setdefault(event.nodeId, event.createdAt)
            if event.nodeId and event.eventType in {"nodeCompleted", "humanDecisionRecorded"}:
                completed_at[event.nodeId] = event.createdAt
        for node in run.nodes:
            state = runtime_nodes[node.nodeId]
            node.status = state.status
            node.progressPercent = state.progressPercent
            node.outputSummary = list(state.result.summary) if state.result else []
            node.startedAt = started_at.get(node.nodeId)
            node.completedAt = completed_at.get(node.nodeId)
        completed_count = sum(node.status == "completed" for node in snapshot.nodes)
        run.status = snapshot.status
        run.currentNodeId = snapshot.currentNodeId
        run.runtimeRevision = snapshot.revision
        run.progressPercent = 100 if snapshot.status == "completed" else min(96, round(completed_count / len(snapshot.nodes) * 100) + (8 if snapshot.currentNodeId else 0))
        title_by_type = {
            "runStarted": "流程运行已开始", "nodeCompleted": "节点已完成",
            "nodeStarted": "节点已开始", "humanReviewRequired": "等待人工确认",
            "runStopped": "运行已终止", "runCompleted": "运行已完成",
            "runResumed": "人工决策已执行", "guidanceApplied": "人工引导已生效",
            "humanDecisionRecorded": "人工验收决策已记录",
            "guidanceScheduled": "人工引导已排队", "guidanceRejected": "人工引导未确认",
            "guidanceAppliedOnRestart": "人工引导已写入新版本",
        }
        run.events = [AgentRunEvent(eventId=event.eventId, eventType=event.eventType, nodeId=event.nodeId, title=title_by_type.get(event.eventType, event.eventType), detail=event.detail, createdAt=event.createdAt) for event in snapshot.events]
        return run

    @staticmethod
    def _assert_guidance_owner(guidance: AgentGuidancePreview, experiment_id: str, run_id: str) -> None:
        if guidance.experimentId != experiment_id or guidance.runId != run_id:
            raise AgentRunConflictError("Guidance belongs to another experiment or run")

    @staticmethod
    def _event(event_type: str, node_id: str | None, title: str, detail: str) -> AgentRunEvent:
        return AgentRunEvent(eventId=f"event-{uuid4().hex[:10]}", eventType=event_type, nodeId=node_id, title=title, detail=detail, createdAt=_now())


_runtime_adapter, _runtime_backend, _runtime_fallback_reason = build_runtime_adapter()
agent_orchestrator = AgentOrchestrator(runtime=_runtime_adapter, runtime_backend=_runtime_backend)
