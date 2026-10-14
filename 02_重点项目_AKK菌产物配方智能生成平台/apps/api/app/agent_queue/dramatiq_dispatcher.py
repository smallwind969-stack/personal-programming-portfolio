from __future__ import annotations

from typing import Protocol


class CommandDispatcher(Protocol):
    def dispatch(self, task_id: str) -> None: ...


class InlinePollDispatcher:
    """SQLite workers poll the ledger, so enqueue needs no external wake-up."""

    def dispatch(self, task_id: str) -> None:
        return None


class DramatiqRedisDispatcher:
    """Redis transports an opaque task id; command payloads remain in the audit ledger."""

    def __init__(self, redis_url: str = "", broker=None) -> None:
        import dramatiq
        if broker is None:
            from app.agent_queue.dramatiq_actors import redis_broker, wake_agent_worker
            self.broker = redis_broker
            self._actor = wake_agent_worker
        else:
            self.broker = broker

            @dramatiq.actor(broker=self.broker, queue_name="agent-commands", max_retries=0)
            def wake_agent_worker(task_id: str) -> None:
                from app.worker import run_once_from_environment
                run_once_from_environment(wake_task_id=task_id)

            self._actor = wake_agent_worker

    def dispatch(self, task_id: str) -> None:
        self._actor.send(task_id)

    def build_message(self, task_id: str):
        return self._actor.message(task_id)
