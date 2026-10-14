from importlib.metadata import PackageNotFoundError, version
import os
from urllib.parse import urlsplit

from fastapi import APIRouter, Query

from app.agent_runtime.factory import langgraph_installed
from app.schemas.runtime import AgentRuntimeStatus, LocalModelCapability, RuntimeBackendCapability
from app.services.agent_orchestrator import agent_orchestrator, _runtime_fallback_reason
from app.services.llm_service import local_llm_service
from app.schemas.agent_commands import AgentCommandTask, AgentCommandSummary, AgentQueueStatus, AgentCommandCancelRequest, AgentCommandReplayRequest
from app.agent_queue.sqlite_queue import AgentCommandConflictError, AgentCommandNotFoundError
from app.services.agent_command_service import agent_command_queue, agent_command_service
from app.agent_registry.builtin import agent_catalog
from app.agent_registry.models import AgentCatalogSnapshot


router = APIRouter(prefix="/agent-runtime", tags=["agent-runtime"])


@router.get("/catalog", response_model=AgentCatalogSnapshot)
def get_agent_catalog() -> AgentCatalogSnapshot:
    return agent_catalog.snapshot()


@router.get("/commands", response_model=list[AgentCommandSummary])
def list_recent_agent_commands(
    limit: int = Query(default=50, ge=1, le=200),
    experiment_id: str | None = Query(default=None, alias="experimentId"),
) -> list[AgentCommandSummary]:
    return [AgentCommandSummary(
        taskId=task.taskId, commandId=task.commandId, experimentId=task.experimentId,
        runId=task.runId, targetKind=task.targetKind, action=task.action,
        status=task.status, attempts=task.attempts, maxAttempts=task.maxAttempts,
        priority=task.priority, resultRevision=task.resultRevision,
        resultRunId=task.resultRunId, errorCategory=task.errorCategory,
        createdAt=task.createdAt, updatedAt=task.updatedAt,
    ) for task in agent_command_queue.list_recent(limit, experiment_id)]


@router.get("/commands/{task_id}", response_model=AgentCommandTask)
def get_agent_command(task_id: str) -> AgentCommandTask:
    try:
        return agent_command_queue.get(task_id)
    except AgentCommandNotFoundError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Agent command not found") from exc


@router.get("/queue/status", response_model=AgentQueueStatus)
def get_agent_queue_status() -> AgentQueueStatus:
    return agent_command_service.status()


@router.post("/commands/{task_id}/cancel", response_model=AgentCommandTask)
def cancel_agent_command(task_id: str, payload: AgentCommandCancelRequest) -> AgentCommandTask:
    try: return agent_command_queue.cancel(task_id, payload.reason)
    except AgentCommandNotFoundError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Agent command not found") from exc
    except AgentCommandConflictError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/commands/{task_id}/replay", response_model=AgentCommandTask)
def replay_agent_command(task_id: str, payload: AgentCommandReplayRequest) -> AgentCommandTask:
    try: return agent_command_queue.replay(task_id, payload.commandId)
    except AgentCommandNotFoundError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Agent command not found") from exc
    except AgentCommandConflictError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _safe_endpoint_label(raw_url: str) -> str:
    parsed = urlsplit(raw_url)
    host = parsed.hostname or "local-endpoint"
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme or 'http'}://{host}{port}"


@router.get("/status", response_model=AgentRuntimeStatus)
def get_agent_runtime_status() -> AgentRuntimeStatus:
    requested = os.getenv("AGENT_RUNTIME_BACKEND", "deterministic").strip().lower()
    effective = agent_orchestrator._runtime_backend
    persistent = effective.endswith("-sqlite")
    snapshots = getattr(agent_orchestrator._runtime, "list_snapshots", lambda: [])()
    return AgentRuntimeStatus(
        requestedBackend=requested,
        effectiveBackend=effective,
        fallbackReason=_runtime_fallback_reason,
        backends=[
            RuntimeBackendCapability(
                backend="deterministic", installed=True, enabled=effective.startswith("deterministic"), version="v1",
                capabilities=["state-graph", "cas", "idempotency", "human-review", "audit-events", "sqlite-recovery" if persistent else "in-process-only"],
            ),
            RuntimeBackendCapability(
                backend="langgraph", installed=langgraph_installed(), enabled=effective.startswith("langgraph"), version=_package_version("langgraph"),
                capabilities=["StateGraph", "SqliteSaver" if persistent else "InMemorySaver", "interrupt-after", "checkpoint-resume", "cross-restart-recovery" if persistent else "in-process-only"],
            ),
        ],
        localModel=LocalModelCapability(
            configured=local_llm_service.enabled,
            provider=local_llm_service.provider,
            model=local_llm_service.model,
            endpointLabel=_safe_endpoint_label(local_llm_service.base_url),
            liveProbeEndpoint="/llm/status",
        ),
        executionBoundary=[
            "LLM 不执行数据清洗、单位换算和数学评估",
            "LLM 不晋升模型或结果版本",
            "LLM 不下发真实产线控制指令",
        ],
        checkpointBackend="sqlite" if persistent else "memory",
        persistent=persistent,
        recoverableRuns=len(snapshots),
    )
