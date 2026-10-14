from app.agent_queue.factory import build_agent_command_queue
from app.agent_queue.sqlite_queue import SqliteAgentCommandQueue
from app.agent_queue.dramatiq_dispatcher import DramatiqRedisDispatcher


def test_queue_factory_defaults_to_sqlite(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AGENT_QUEUE_BACKEND", raising=False)
    queue, status = build_agent_command_queue(tmp_path / "queue.db")
    assert isinstance(queue, SqliteAgentCommandQueue)
    assert status.requestedBackend == "sqlite"
    assert status.effectiveBackend == "sqlite"
    assert status.fallbackReason is None


def test_queue_factory_safely_falls_back_when_redis_is_not_configured(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AGENT_QUEUE_BACKEND", "dramatiq-redis")
    monkeypatch.delenv("AGENT_REDIS_URL", raising=False)
    queue, status = build_agent_command_queue(tmp_path / "queue.db")
    assert isinstance(queue, SqliteAgentCommandQueue)
    assert status.requestedBackend == "dramatiq-redis"
    assert status.effectiveBackend == "sqlite"
    assert "AGENT_REDIS_URL" in status.fallbackReason


def test_dramatiq_message_contains_only_opaque_task_id() -> None:
    from dramatiq.brokers.stub import StubBroker

    dispatcher = DramatiqRedisDispatcher(broker=StubBroker())
    message = dispatcher.build_message("agent-task-safe123")
    assert message.args == ("agent-task-safe123",)
    assert message.kwargs == {}
    assert "experiment" not in message.asdict()
