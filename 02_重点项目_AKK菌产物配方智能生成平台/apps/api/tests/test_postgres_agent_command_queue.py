from pathlib import Path
import os

import pytest

from app.agent_queue.factory import build_agent_command_queue
from app.agent_queue.postgres_queue import PostgresAgentCommandQueue
from app.agent_queue.protocol import AgentCommandQueue
from app.schemas.agent_commands import AgentCommandCreate


def test_postgres_migration_uses_non_blocking_row_lock_and_json_resource_match() -> None:
    sql = (Path(__file__).parents[1] / "app" / "agent_queue" / "migrations" / "001_agent_command_ledger.sql").read_text(encoding="utf-8")
    assert "FOR UPDATE SKIP LOCKED" in PostgresAgentCommandQueue.CLAIM_SQL
    assert "required_capabilities" in sql
    assert "JSONB" in sql
    assert "agent_workers" in sql


def test_postgres_queue_structurally_satisfies_queue_protocol() -> None:
    required = {name for name, value in AgentCommandQueue.__dict__.items() if callable(value)}
    assert required <= set(dir(PostgresAgentCommandQueue))


def test_factory_falls_back_when_postgres_url_is_missing(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AGENT_QUEUE_BACKEND", "postgres")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    queue, status = build_agent_command_queue(tmp_path / "fallback.db")
    assert status.requestedBackend == "postgres"
    assert status.effectiveBackend == "sqlite"
    assert "DATABASE_URL" in status.fallbackReason


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="TEST_POSTGRES_URL not configured")
def test_postgres_live_idempotency_resource_claim_and_fencing() -> None:
    queue = PostgresAgentCommandQueue(os.environ["TEST_POSTGRES_URL"], namespace="step039_test")
    queue.reset()
    request = AgentCommandCreate(commandId="pg-cmd", experimentId="pg-exp", runId="pg-run", action="advance", expectedRevision=1, requiredCapabilities=["cpu", "gpu"])
    first = queue.enqueue(request)
    assert queue.enqueue(request).taskId == first.taskId
    assert queue.claim("cpu-only", capabilities={"cpu"}) is None
    leased = queue.claim("gpu-node", capabilities={"cpu", "gpu"})
    completed = queue.complete(leased.taskId, "gpu-node", leased.leaseToken, 2)
    assert completed.status == "completed"
