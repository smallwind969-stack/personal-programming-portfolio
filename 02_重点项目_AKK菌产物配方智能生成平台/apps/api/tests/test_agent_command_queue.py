from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from app.agent_queue.sqlite_queue import AgentCommandConflictError, AgentLeaseConflictError, SqliteAgentCommandQueue
from app.schemas.agent_commands import AgentCommandCreate
from app.services.agent_command_service import AgentCommandService
from app.services.agent_orchestrator import agent_orchestrator
from app.feature_binding_advisor.contracts import DeviceAdapterPackSelector


class Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 7, 20, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: int) -> None:
        self.value += timedelta(seconds=seconds)


def command(command_id: str = "cmd-1", revision: int = 1, max_attempts: int = 3) -> AgentCommandCreate:
    return AgentCommandCreate(
        commandId=command_id, experimentId="exp-1", runId="run-1", action="advance",
        expectedRevision=revision, payload={}, maxAttempts=max_attempts,
    )


def test_binding_suggestion_enqueue_uses_adaptation_agent_capabilities(tmp_path) -> None:
    queue = SqliteAgentCommandQueue(tmp_path / "binding-queue.db")
    service = AgentCommandService(queue, agent_orchestrator)

    selector = DeviceAdapterPackSelector(
        enterpriseKey="enterprise-a", deviceType="reactor", packVersion="1.0.0",
    )
    task = service.enqueue_binding_suggestion(
        "exp-real", "model-v1", "binding-command", priority=2, adapter_pack=selector,
    )

    assert task.targetKind == "adaptation"
    assert task.action == "featureBindingSuggest"
    assert task.runId == "model-v1"
    assert task.requiredCapabilities == ["cpu"]
    assert task.priority == 2
    assert task.payload["adapterPack"] == selector.model_dump(mode="json")


def test_enqueue_is_idempotent_but_rejects_command_reuse_with_different_payload(tmp_path) -> None:
    queue = SqliteAgentCommandQueue(tmp_path / "queue.db")
    first = queue.enqueue(command())
    second = queue.enqueue(command())
    assert first.taskId == second.taskId
    with pytest.raises(AgentCommandConflictError):
        queue.enqueue(command(revision=2))


def test_only_one_worker_can_claim_a_command(tmp_path) -> None:
    queue = SqliteAgentCommandQueue(tmp_path / "queue.db")
    queue.enqueue(command())
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda worker: queue.claim(worker, lease_seconds=30), ["worker-a", "worker-b"]))
    assert sum(item is not None for item in claims) == 1
    claimed = next(item for item in claims if item)
    assert claimed.status == "leased" and claimed.leaseToken


def test_heartbeat_extends_lease_and_fencing_token_rejects_stale_worker(tmp_path) -> None:
    clock = Clock()
    queue = SqliteAgentCommandQueue(tmp_path / "queue.db", clock=clock)
    queue.enqueue(command())
    first = queue.claim("worker-a", lease_seconds=10)
    assert first is not None
    clock.advance(8)
    extended = queue.heartbeat(first.taskId, "worker-a", first.leaseToken, lease_seconds=10)
    clock.advance(5)
    assert queue.claim("worker-b", lease_seconds=10) is None
    clock.advance(6)
    second = queue.claim("worker-b", lease_seconds=10)
    assert second is not None and second.leaseToken != extended.leaseToken
    with pytest.raises(AgentLeaseConflictError):
        queue.complete(first.taskId, "worker-a", first.leaseToken, result_revision=2)
    completed = queue.complete(second.taskId, "worker-b", second.leaseToken, result_revision=2)
    assert completed.status == "completed"


def test_retry_then_dead_letter_after_max_attempts(tmp_path) -> None:
    queue = SqliteAgentCommandQueue(tmp_path / "queue.db")
    queue.enqueue(command(max_attempts=2))
    first = queue.claim("worker-a", 30)
    retried = queue.fail(first.taskId, "worker-a", first.leaseToken, "transient", "temporary", retryable=True)
    assert retried.status == "queued"
    second = queue.claim("worker-b", 30)
    dead = queue.fail(second.taskId, "worker-b", second.leaseToken, "transient", "again", retryable=True)
    assert dead.status == "deadLetter" and dead.attempts == 2


def test_queue_state_survives_new_adapter_instance(tmp_path) -> None:
    path = tmp_path / "queue.db"
    first = SqliteAgentCommandQueue(path)
    queued = first.enqueue(command())
    restored = SqliteAgentCommandQueue(path)
    assert restored.get(queued.taskId).commandId == "cmd-1"
    assert restored.counts()["queued"] == 1


def test_priority_and_experiment_concurrency_limit_control_claim_order(tmp_path) -> None:
    queue = SqliteAgentCommandQueue(tmp_path / "queue.db", max_active_per_experiment=1)
    low = command("low").model_copy(update={"priority": 1})
    high = command("high").model_copy(update={"priority": 9})
    other = command("other").model_copy(update={"experimentId": "exp-2", "priority": 2})
    queue.enqueue(low); queue.enqueue(high); queue.enqueue(other)
    first = queue.claim("worker-a", 30)
    assert first.commandId == "high"
    second = queue.claim("worker-b", 30)
    assert second.commandId == "other"
    assert queue.claim("worker-c", 30) is None


def test_queued_task_can_be_cancelled_and_dead_letter_can_be_replayed(tmp_path) -> None:
    queue = SqliteAgentCommandQueue(tmp_path / "queue.db")
    queued = queue.enqueue(command("cancel-me"))
    cancelled = queue.cancel(queued.taskId, "用户改变实验计划")
    assert cancelled.status == "cancelled" and cancelled.cancelledAt

    dead_source = queue.enqueue(command("dead", max_attempts=1))
    leased = queue.claim("worker-a", 30)
    assert leased.taskId == dead_source.taskId
    dead = queue.fail(leased.taskId, "worker-a", leased.leaseToken, "transient", "failed", retryable=True)
    replayed = queue.replay(dead.taskId, "replay-dead")
    assert replayed.status == "queued" and replayed.parentTaskId == dead.taskId and replayed.attempts == 0


def test_claim_only_selects_tasks_supported_by_worker_capabilities(tmp_path) -> None:
    queue = SqliteAgentCommandQueue(tmp_path / "queue.db")
    queue.enqueue(command("gpu-task").model_copy(update={"requiredCapabilities": ["cpu", "gpu"]}))
    queue.enqueue(command("llm-task").model_copy(update={"experimentId": "exp-2", "requiredCapabilities": ["cpu", "localLlm"]}))

    assert queue.claim("cpu-worker", capabilities={"cpu"}) is None
    gpu = queue.claim("gpu-worker", capabilities={"cpu", "gpu"})
    assert gpu is not None and gpu.commandId == "gpu-task"
    llm = queue.claim("llm-worker", capabilities={"cpu", "localLlm"})
    assert llm is not None and llm.commandId == "llm-task"


def test_worker_registry_reports_capacity_and_stale_workers(tmp_path) -> None:
    clock = Clock()
    queue = SqliteAgentCommandQueue(tmp_path / "queue.db", clock=clock)
    queue.register_worker("worker-a", {"cpu", "localLlm"}, max_concurrent=2, labels={"host": "lab-a"})
    active = queue.worker_status(stale_after_seconds=30)
    assert active[0].workerId == "worker-a"
    assert active[0].status == "online"
    assert active[0].capabilities == ["cpu", "localLlm"]
    assert active[0].activeTasks == 0 and active[0].availableSlots == 2
    clock.advance(31)
    assert queue.worker_status(stale_after_seconds=30)[0].status == "offline"


def test_legacy_claim_defaults_to_all_capabilities_for_backward_compatibility(tmp_path) -> None:
    queue = SqliteAgentCommandQueue(tmp_path / "queue.db")
    queue.enqueue(command("gpu-task").model_copy(update={"requiredCapabilities": ["gpu"]}))
    assert queue.claim("legacy-worker") is not None


def test_registered_worker_capacity_is_enforced_across_experiments(tmp_path) -> None:
    queue = SqliteAgentCommandQueue(tmp_path / "queue.db")
    queue.register_worker("bounded", {"cpu"}, max_concurrent=1)
    queue.enqueue(command("one"))
    queue.enqueue(command("two").model_copy(update={"experimentId": "exp-2"}))
    assert queue.claim("bounded", capabilities={"cpu"}) is not None
    assert queue.claim("bounded", capabilities={"cpu"}) is None
    assert queue.claim("other", capabilities={"cpu"}) is not None


def test_recent_commands_are_reverse_chronological_and_bounded(tmp_path) -> None:
    queue = SqliteAgentCommandQueue(tmp_path / "recent.db")
    first = queue.enqueue(command("recent-1").model_copy(update={"experimentId": "exp-a"}))
    second = queue.enqueue(command("recent-2").model_copy(update={"experimentId": "exp-b"}))

    recent = queue.list_recent(limit=1)
    filtered = queue.list_recent(limit=10, experiment_id="exp-a")

    assert [item.taskId for item in recent] == [second.taskId]
    assert [item.taskId for item in filtered] == [first.taskId]
