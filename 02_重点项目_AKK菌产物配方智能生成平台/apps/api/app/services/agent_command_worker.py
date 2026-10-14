from __future__ import annotations

from threading import Event, Thread

from app.agent_queue.sqlite_queue import AgentLeaseConflictError
from app.agent_queue.protocol import AgentCommandQueue
from app.schemas.agent_commands import AgentCommandTask
from app.agent_registry.execution import AgentExecutionRegistry, build_execution_registry
from app.services.agent_orchestrator import AgentOrchestrator, AgentRunConflictError, AgentRunNotFoundError
from app.services.simulation_run_orchestrator import SimulationRunOrchestrator, SimulationRunConflictError, SimulationRunNotFoundError, simulation_run_orchestrator
from app.services.optimization_orchestrator import OptimizationOrchestrator, OptimizationConflictError, OptimizationNotFoundError, optimization_orchestrator


class AgentCommandWorker:
    def __init__(self, queue: AgentCommandQueue, orchestrator: AgentOrchestrator, worker_id: str, lease_seconds: int = 30, simulation: SimulationRunOrchestrator | None = None, optimization: OptimizationOrchestrator | None = None, capabilities: set[str] | None = None, max_concurrent: int = 1, labels: dict[str, str] | None = None, execution_registry: AgentExecutionRegistry | None = None, research=None, binding_advisor=None) -> None:
        self.queue = queue
        self.orchestrator = orchestrator
        self.workerId = worker_id
        self.leaseSeconds = lease_seconds
        self.simulation = simulation or simulation_run_orchestrator
        self.optimization = optimization or optimization_orchestrator
        self.capabilities = capabilities or {"cpu"}
        self.maxConcurrent = max_concurrent
        self.labels = labels or {}
        self.executionRegistry = execution_registry or build_execution_registry(
            self.orchestrator, self.simulation, self.optimization, research, binding_advisor,
        )

    def run_once(self) -> AgentCommandTask | None:
        self.queue.register_worker(self.workerId, self.capabilities, self.maxConcurrent, self.labels)
        task = self.queue.claim(self.workerId, self.leaseSeconds, self.capabilities)
        if task is None:
            return None
        token = task.leaseToken
        if token is None:
            raise AgentLeaseConflictError("claimed task has no lease token")
        try:
            self.queue.heartbeat(task.taskId, self.workerId, token, self.leaseSeconds)
            if self.queue.get(task.taskId).cancelRequestedAt:
                return self.queue.acknowledge_cancel(task.taskId, self.workerId, token)
            self.orchestrator.refresh_recovered_runs()
            self.simulation.refresh(); self.optimization.refresh()
            stop_heartbeat = Event()
            heartbeat_error: list[BaseException] = []
            heartbeat = Thread(
                target=self._heartbeat_loop,
                args=(task.taskId, token, stop_heartbeat, heartbeat_error),
                name=f"agent-heartbeat-{task.taskId}", daemon=True,
            )
            heartbeat.start()
            try:
                result_revision, result_run_id = self.executionRegistry.execute(task.action, task)
            finally:
                stop_heartbeat.set(); heartbeat.join(timeout=2)
            if heartbeat_error:
                raise AgentLeaseConflictError(str(heartbeat_error[0]))
            return self.queue.complete(task.taskId, self.workerId, token, result_revision, result_run_id)
        except (AgentRunConflictError, AgentRunNotFoundError, SimulationRunConflictError, SimulationRunNotFoundError, OptimizationConflictError, OptimizationNotFoundError) as exc:
            return self.queue.fail(task.taskId, self.workerId, token, "conflict", str(exc), retryable=False)
        except AgentLeaseConflictError:
            raise
        except Exception as exc:
            return self.queue.fail(task.taskId, self.workerId, token, type(exc).__name__, str(exc), retryable=True, delay_seconds=min(30, 2 ** task.attempts))

    def _heartbeat_loop(self, task_id: str, lease_token: str, stopped: Event, errors: list[BaseException]) -> None:
        interval = max(0.1, min(10.0, self.leaseSeconds / 3))
        while not stopped.wait(interval):
            try:
                self.queue.heartbeat(task_id, self.workerId, lease_token, self.leaseSeconds)
            except BaseException as exc:
                errors.append(exc)
                stopped.set()
                return
