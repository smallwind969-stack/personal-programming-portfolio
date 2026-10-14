from __future__ import annotations

import os

from app.agent_queue.factory import build_agent_command_queue
from app.agent_queue.protocol import AgentCommandQueue
from app.agent_queue.dramatiq_dispatcher import DramatiqRedisDispatcher, InlinePollDispatcher
from app.schemas.agent_commands import AgentCommandCreate, AgentCommandEnqueueRequest, AgentCommandTask, AgentQueueStatus, UnifiedAgentCommandEnqueueRequest
from app.services.agent_orchestrator import AgentOrchestrator, agent_orchestrator
from app.agent_registry.builtin import agent_catalog
from app.feature_binding_advisor.contracts import DeviceAdapterPackSelector


_queue_path = os.getenv("AGENT_COMMAND_QUEUE_PATH", ":memory:").strip() or ":memory:"
agent_command_queue, _queue_backend_status = build_agent_command_queue(_queue_path)
_dispatch_backend = os.getenv("AGENT_DISPATCH_BACKEND", "dramatiq-redis" if _queue_backend_status.effectiveBackend == "dramatiq-redis" else "polling").strip().lower()
try:
    _dispatcher = DramatiqRedisDispatcher(os.getenv("AGENT_REDIS_URL", "")) if _dispatch_backend == "dramatiq-redis" else InlinePollDispatcher()
except Exception as exc:
    _queue_backend_status = type(_queue_backend_status)(
        _queue_backend_status.requestedBackend, "sqlite", f"dramatiq-redis initialization failed: {type(exc).__name__}"
    )
    _dispatcher = InlinePollDispatcher()
    _dispatch_backend = "polling"


class AgentCommandService:
    def __init__(self, queue: AgentCommandQueue, orchestrator: AgentOrchestrator) -> None:
        self.queue = queue
        self.orchestrator = orchestrator

    def enqueue(self, experiment_id: str, run_id: str, request: AgentCommandEnqueueRequest) -> AgentCommandTask:
        run = self.orchestrator.get_run(experiment_id, run_id)
        current = next((node for node in run.nodes if node.nodeId == run.currentNodeId), None)
        required = agent_catalog.agent(current.agentKey).requiredWorkerCapabilities if current else ["cpu"]
        task = self.queue.enqueue(AgentCommandCreate(
            commandId=request.commandId, experimentId=experiment_id, runId=run_id,
            action=request.action, expectedRevision=request.expectedRevision,
            payload=request.payload, maxAttempts=request.maxAttempts, priority=request.priority,
            requiredCapabilities=_infer_required_capabilities(required, request.payload),
        ))
        _dispatcher.dispatch(task.taskId)
        return task

    def status(self) -> AgentQueueStatus:
        persistent = _queue_backend_status.effectiveBackend == "postgres" or _queue_path != ":memory:"
        return AgentQueueStatus(
            backend=_queue_backend_status.effectiveBackend if _queue_backend_status.effectiveBackend in {"postgres", "dramatiq-redis"} else ("sqlite" if persistent else "memory-sqlite"),
            persistent=persistent,
            counts=self.queue.counts(),
            requestedBackend=_queue_backend_status.requestedBackend,
            fallbackReason=_queue_backend_status.fallbackReason,
            dispatchBackend="dramatiq-redis" if _dispatch_backend == "dramatiq-redis" else "polling",
            workers=self.queue.worker_status(),
        )

    def enqueue_domain(self, experiment_id: str, request: UnifiedAgentCommandEnqueueRequest) -> AgentCommandTask:
        task = self.queue.enqueue(AgentCommandCreate(
            commandId=request.commandId, experimentId=experiment_id, runId=request.runId,
            targetKind=request.targetKind, action=request.action, expectedRevision=request.expectedRevision,
            payload=request.payload, maxAttempts=request.maxAttempts, priority=request.priority,
            requiredCapabilities=_infer_required_capabilities(agent_catalog.agent(request.targetKind).requiredWorkerCapabilities, request.payload),
        ))
        _dispatcher.dispatch(task.taskId)
        return task

    def enqueue_research_trial(self, experiment_id: str, campaign_id: str, command_id: str, hypothesis: str, parameter_patch: dict, priority: int = 0) -> AgentCommandTask:
        task = self.queue.enqueue(AgentCommandCreate(
            commandId=command_id, experimentId=experiment_id, runId=campaign_id, targetKind="research", action="researchTrial",
            expectedRevision=1, payload={"hypothesis": hypothesis, "parameterPatch": parameter_patch}, maxAttempts=2,
            priority=priority, requiredCapabilities=agent_catalog.agent("researchExperiment").requiredWorkerCapabilities,
        ))
        _dispatcher.dispatch(task.taskId)
        return task

    def enqueue_binding_suggestion(
        self, experiment_id: str, model_version: str, command_id: str, priority: int = 0,
        adapter_pack: DeviceAdapterPackSelector | None = None,
    ) -> AgentCommandTask:
        task = self.queue.enqueue(AgentCommandCreate(
            commandId=command_id, experimentId=experiment_id, runId=model_version,
            targetKind="adaptation", action="featureBindingSuggest", expectedRevision=1,
            payload={"adapterPack": adapter_pack.model_dump(mode="json")} if adapter_pack else {},
            maxAttempts=2, priority=priority,
            requiredCapabilities=agent_catalog.agent("featureBindingAdvisor").requiredWorkerCapabilities,
        ))
        _dispatcher.dispatch(task.taskId)
        return task


def _infer_required_capabilities(manifest_requirements: list[str], payload: dict) -> list[str]:
    required = set(manifest_requirements)
    if payload.get("requiresGpu") is True:
        required.add("gpu")
    if payload.get("requiresLocalLlm") is True:
        required.add("localLlm")
    return sorted(required)


agent_command_service = AgentCommandService(agent_command_queue, agent_orchestrator)
