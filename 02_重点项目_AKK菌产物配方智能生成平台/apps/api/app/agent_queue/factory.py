from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from app.agent_queue.sqlite_queue import SqliteAgentCommandQueue
from app.agent_queue.protocol import AgentCommandQueue


@dataclass(frozen=True)
class AgentQueueBackendStatus:
    requestedBackend: str
    effectiveBackend: str
    fallbackReason: str | None = None


def build_agent_command_queue(path: str | Path = ":memory:") -> tuple[AgentCommandQueue, AgentQueueBackendStatus]:
    requested = os.getenv("AGENT_QUEUE_BACKEND", "sqlite").strip().lower() or "sqlite"
    if requested == "sqlite":
        return SqliteAgentCommandQueue(path), AgentQueueBackendStatus(requested, "sqlite")
    if requested == "postgres":
        database_url = os.getenv("DATABASE_URL", "").strip()
        if not database_url:
            return SqliteAgentCommandQueue(path), AgentQueueBackendStatus(requested, "sqlite", "DATABASE_URL is required for postgres")
        try:
            from app.agent_queue.postgres_queue import PostgresAgentCommandQueue
            queue = PostgresAgentCommandQueue(database_url, namespace=os.getenv("AGENT_QUEUE_NAMESPACE", "default"))
            return queue, AgentQueueBackendStatus(requested, "postgres")
        except Exception as exc:
            return SqliteAgentCommandQueue(path), AgentQueueBackendStatus(requested, "sqlite", f"postgres initialization failed: {type(exc).__name__}")
    if requested == "dramatiq-redis":
        redis_url = os.getenv("AGENT_REDIS_URL", "").strip()
        if not redis_url:
            return SqliteAgentCommandQueue(path), AgentQueueBackendStatus(requested, "sqlite", "AGENT_REDIS_URL is required for dramatiq-redis")
        try:
            import dramatiq  # noqa: F401
            import redis  # noqa: F401
        except ImportError as exc:
            return SqliteAgentCommandQueue(path), AgentQueueBackendStatus(requested, "sqlite", f"dramatiq-redis dependency unavailable: {exc.name}")
        # Backward-compatible Step038 mode: Redis transport with a SQLite ledger.
        return SqliteAgentCommandQueue(path), AgentQueueBackendStatus(requested, "dramatiq-redis")
    return SqliteAgentCommandQueue(path), AgentQueueBackendStatus(requested, "sqlite", f"unsupported queue backend: {requested}")
