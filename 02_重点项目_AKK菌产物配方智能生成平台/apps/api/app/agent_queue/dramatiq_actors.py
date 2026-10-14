from __future__ import annotations

import os

import dramatiq
from dramatiq.brokers.redis import RedisBroker


redis_broker = RedisBroker(url=os.getenv("AGENT_REDIS_URL", "redis://redis:6379/0"))
dramatiq.set_broker(redis_broker)


@dramatiq.actor(broker=redis_broker, queue_name="agent-commands", max_retries=0)
def wake_agent_worker(task_id: str) -> None:
    """Wake one resource-aware ledger poll; task_id is intentionally opaque."""
    from app.worker import run_once_from_environment

    run_once_from_environment(wake_task_id=task_id)
