from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

from app.agent_queue.sqlite_queue import AgentCommandConflictError, AgentCommandNotFoundError, AgentLeaseConflictError
from app.schemas.agent_commands import AgentCommandCreate, AgentCommandTask, AgentWorkerStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PostgresAgentCommandQueue:
    """Multi-host command ledger using PostgreSQL row locks and fencing tokens."""

    CLAIM_SQL = """
    WITH candidate AS (
        SELECT task_id FROM agent_command_tasks t
        WHERE namespace=%s AND attempts < max_attempts
          AND ((status='queued' AND available_at<=%s) OR (status='leased' AND lease_expires_at<=%s))
          AND required_capabilities <@ %s::jsonb
          AND (SELECT COUNT(*) FROM agent_command_tasks active
               WHERE active.namespace=t.namespace AND active.experiment_id=t.experiment_id
                 AND active.status='leased' AND active.lease_expires_at>%s) < %s
          AND (SELECT COUNT(*) FROM agent_command_tasks owned WHERE owned.namespace=t.namespace
               AND owned.status='leased' AND owned.lease_owner=%s AND owned.lease_expires_at>%s)
              < COALESCE((SELECT max_concurrent FROM agent_workers w WHERE w.namespace=t.namespace AND w.worker_id=%s), 1000000)
        ORDER BY priority DESC, created_at, task_id
        FOR UPDATE SKIP LOCKED LIMIT 1
    )
    UPDATE agent_command_tasks t SET status='leased', attempts=t.attempts+1,
      lease_owner=%s, lease_token=%s, lease_expires_at=%s, heartbeat_at=%s,
      error_category=NULL, error_message=NULL, updated_at=%s
    FROM candidate WHERE t.namespace=%s AND t.task_id=candidate.task_id RETURNING t.*
    """

    def __init__(self, database_url: str, namespace: str = "default", min_pool_size: int = 1, max_pool_size: int = 8, max_active_per_experiment: int = 1) -> None:
        if not database_url:
            raise ValueError("database_url is required")
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        self.namespace = namespace
        self.maxActivePerExperiment = max_active_per_experiment
        self._pool = ConnectionPool(database_url, min_size=min_pool_size, max_size=max_pool_size, kwargs={"row_factory": dict_row}, open=True)
        self._migrate()

    def _migrate(self) -> None:
        migration = Path(__file__).with_name("migrations").joinpath("001_agent_command_ledger.sql").read_text(encoding="utf-8")
        with self._pool.connection() as conn:
            conn.execute(migration)

    def close(self) -> None:
        self._pool.close()

    def reset(self) -> None:
        with self._pool.connection() as conn:
            conn.execute("DELETE FROM agent_command_tasks WHERE namespace=%s", (self.namespace,))
            conn.execute("DELETE FROM agent_workers WHERE namespace=%s", (self.namespace,))

    def enqueue(self, request: AgentCommandCreate) -> AgentCommandTask:
        canonical = json.dumps(request.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        fingerprint = f"sha256:{sha256(canonical.encode('utf-8')).hexdigest()}"
        now = _utcnow(); task_id = f"agent-task-{uuid4().hex[:12]}"
        with self._pool.connection() as conn:
            existing = conn.execute("SELECT * FROM agent_command_tasks WHERE namespace=%s AND command_id=%s", (self.namespace, request.commandId)).fetchone()
            if existing:
                if existing["request_fingerprint"] != fingerprint:
                    raise AgentCommandConflictError("commandId has already been used with a different request")
                return self._task(existing)
            row = conn.execute(
                    """INSERT INTO agent_command_tasks(namespace, task_id, command_id, request_fingerprint, experiment_id, run_id,
                    target_kind, action, expected_revision, payload, required_capabilities, max_attempts, priority, parent_task_id,
                    status, attempts, available_at, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s,'queued',0,%s,%s,%s)
                    ON CONFLICT(namespace, command_id) DO NOTHING RETURNING *""",
                    (self.namespace, task_id, request.commandId, fingerprint, request.experimentId, request.runId,
                     request.targetKind, request.action, request.expectedRevision, json.dumps(request.payload),
                     json.dumps(sorted(set(request.requiredCapabilities))), request.maxAttempts, request.priority,
                     request.parentTaskId, now, now, now),
            ).fetchone()
            if row:
                return self._task(row)
            existing = conn.execute("SELECT * FROM agent_command_tasks WHERE namespace=%s AND command_id=%s", (self.namespace, request.commandId)).fetchone()
            if existing["request_fingerprint"] != fingerprint:
                raise AgentCommandConflictError("commandId has already been used with a different request")
            return self._task(existing)

    def claim(self, worker_id: str, lease_seconds: int = 30, capabilities: set[str] | None = None) -> AgentCommandTask | None:
        if not worker_id or lease_seconds < 1:
            raise ValueError("worker_id and positive lease_seconds are required")
        now = _utcnow(); token = f"lease-{uuid4().hex}"; expires = now + timedelta(seconds=lease_seconds)
        allowed = sorted(capabilities or {"cpu", "gpu", "localLlm"})
        with self._pool.connection() as conn:
            conn.execute("""UPDATE agent_command_tasks SET status='deadLetter', error_category='leaseExpired',
                error_message='lease expired after maximum attempts', lease_owner=NULL, lease_token=NULL,
                lease_expires_at=NULL, updated_at=%s WHERE namespace=%s AND status='leased'
                AND lease_expires_at<=%s AND attempts>=max_attempts""", (now, self.namespace, now))
            row = conn.execute(self.CLAIM_SQL, (self.namespace, now, now, json.dumps(allowed), now,
                               self.maxActivePerExperiment, worker_id, now, worker_id,
                               worker_id, token, expires, now, now, self.namespace)).fetchone()
            return self._task(row) if row else None

    def heartbeat(self, task_id: str, worker_id: str, lease_token: str, lease_seconds: int = 30) -> AgentCommandTask:
        now = _utcnow()
        return self._leased_update(task_id, worker_id, lease_token,
            "heartbeat_at=%s, lease_expires_at=%s, updated_at=%s", (now, now + timedelta(seconds=lease_seconds), now))

    def complete(self, task_id: str, worker_id: str, lease_token: str, result_revision: int, result_run_id: str | None = None) -> AgentCommandTask:
        now = _utcnow()
        return self._leased_update(task_id, worker_id, lease_token,
            "status='completed', result_revision=%s, result_run_id=%s, lease_owner=NULL, lease_token=NULL, lease_expires_at=NULL, updated_at=%s",
            (result_revision, result_run_id, now))

    def fail(self, task_id: str, worker_id: str, lease_token: str, category: str, message: str, retryable: bool, delay_seconds: int = 0) -> AgentCommandTask:
        current = self.get(task_id); retry = retryable and current.attempts < current.maxAttempts
        now = _utcnow(); status = "queued" if retry else "deadLetter"
        return self._leased_update(task_id, worker_id, lease_token,
            "status=%s, available_at=%s, lease_owner=NULL, lease_token=NULL, lease_expires_at=NULL, error_category=%s, error_message=%s, updated_at=%s",
            (status, now + timedelta(seconds=max(0, delay_seconds)), category, message[:2000], now))

    def _leased_update(self, task_id: str, worker_id: str, lease_token: str, assignments: str, values: tuple) -> AgentCommandTask:
        now = _utcnow()
        with self._pool.connection() as conn:
            row = conn.execute(f"""UPDATE agent_command_tasks SET {assignments} WHERE namespace=%s AND task_id=%s
                AND status='leased' AND lease_owner=%s AND lease_token=%s AND lease_expires_at>%s RETURNING *""",
                (*values, self.namespace, task_id, worker_id, lease_token, now)).fetchone()
            if row is None:
                raise AgentLeaseConflictError("lease is missing, expired, or owned by another worker")
            return self._task(row)

    def get(self, task_id: str) -> AgentCommandTask:
        with self._pool.connection() as conn:
            row = conn.execute("SELECT * FROM agent_command_tasks WHERE namespace=%s AND task_id=%s", (self.namespace, task_id)).fetchone()
        if row is None:
            raise AgentCommandNotFoundError(task_id)
        return self._task(row)

    def cancel(self, task_id: str, reason: str) -> AgentCommandTask:
        now = _utcnow()
        with self._pool.connection() as conn:
            row = conn.execute("SELECT * FROM agent_command_tasks WHERE namespace=%s AND task_id=%s FOR UPDATE", (self.namespace, task_id)).fetchone()
            if row is None: raise AgentCommandNotFoundError(task_id)
            if row["status"] == "queued":
                result = conn.execute("""UPDATE agent_command_tasks SET status='cancelled', cancelled_at=%s,
                    error_category='cancelled', error_message=%s, updated_at=%s WHERE namespace=%s AND task_id=%s RETURNING *""",
                    (now, reason, now, self.namespace, task_id)).fetchone()
            elif row["status"] == "leased":
                result = conn.execute("""UPDATE agent_command_tasks SET cancel_requested_at=%s, error_category='cancelRequested',
                    error_message=%s, updated_at=%s WHERE namespace=%s AND task_id=%s RETURNING *""",
                    (now, reason, now, self.namespace, task_id)).fetchone()
            else: raise AgentCommandConflictError(f"task in {row['status']} state cannot be cancelled")
            return self._task(result)

    def replay(self, task_id: str, command_id: str) -> AgentCommandTask:
        source = self.get(task_id)
        if source.status != "deadLetter": raise AgentCommandConflictError("only a dead-letter task can be replayed")
        return self.enqueue(AgentCommandCreate(commandId=command_id, experimentId=source.experimentId, runId=source.runId,
            targetKind=source.targetKind, action=source.action, expectedRevision=source.expectedRevision, payload=source.payload,
            maxAttempts=source.maxAttempts, priority=source.priority, parentTaskId=source.taskId,
            requiredCapabilities=source.requiredCapabilities))

    def acknowledge_cancel(self, task_id: str, worker_id: str, lease_token: str) -> AgentCommandTask:
        current = self.get(task_id)
        if not current.cancelRequestedAt: raise AgentCommandConflictError("task has no cancellation request")
        now = _utcnow()
        return self._leased_update(task_id, worker_id, lease_token,
            "status='cancelled', cancelled_at=%s, lease_owner=NULL, lease_token=NULL, lease_expires_at=NULL, updated_at=%s", (now, now))

    def counts(self) -> dict[str, int]:
        result = {key: 0 for key in ("queued", "leased", "completed", "failed", "deadLetter", "cancelled")}
        with self._pool.connection() as conn:
            rows = conn.execute("SELECT status, COUNT(*) count FROM agent_command_tasks WHERE namespace=%s GROUP BY status", (self.namespace,)).fetchall()
        for row in rows: result[row["status"]] = row["count"]
        return result

    def list_recent(self, limit: int = 50, experiment_id: str | None = None) -> list[AgentCommandTask]:
        if limit < 1 or limit > 200: raise ValueError("limit must be between 1 and 200")
        query = "SELECT * FROM agent_command_tasks WHERE namespace=%s"
        parameters: list = [self.namespace]
        if experiment_id:
            query += " AND experiment_id=%s"
            parameters.append(experiment_id)
        query += " ORDER BY created_at DESC, task_id DESC LIMIT %s"
        parameters.append(limit)
        with self._pool.connection() as conn:
            rows = conn.execute(query, tuple(parameters)).fetchall()
        return [self._task(row) for row in rows]

    def register_worker(self, worker_id: str, capabilities: set[str], max_concurrent: int = 1, labels: dict[str, str] | None = None) -> AgentWorkerStatus:
        if not worker_id or not capabilities or max_concurrent < 1: raise ValueError("worker registration is invalid")
        now = _utcnow()
        with self._pool.connection() as conn:
            row = conn.execute("""INSERT INTO agent_workers(namespace, worker_id, capabilities, max_concurrent, labels, heartbeat_at)
                VALUES (%s,%s,%s::jsonb,%s,%s::jsonb,%s) ON CONFLICT(namespace, worker_id) DO UPDATE SET
                capabilities=excluded.capabilities, max_concurrent=excluded.max_concurrent, labels=excluded.labels,
                heartbeat_at=excluded.heartbeat_at RETURNING *""",
                (self.namespace, worker_id, json.dumps(sorted(capabilities)), max_concurrent, json.dumps(labels or {}), now)).fetchone()
        return self._worker(row, now - timedelta(seconds=60))

    def worker_status(self, stale_after_seconds: int = 60) -> list[AgentWorkerStatus]:
        cutoff = _utcnow() - timedelta(seconds=stale_after_seconds)
        with self._pool.connection() as conn:
            rows = conn.execute("""SELECT w.*, (SELECT COUNT(*) FROM agent_command_tasks t WHERE t.namespace=w.namespace
                AND t.status='leased' AND t.lease_owner=w.worker_id AND t.lease_expires_at>%s) AS active_tasks
                FROM agent_workers w WHERE w.namespace=%s ORDER BY worker_id""", (_utcnow(), self.namespace)).fetchall()
        return [self._worker(row, cutoff) for row in rows]

    @staticmethod
    def _iso(value) -> str | None:
        return value.isoformat() if isinstance(value, datetime) else value

    @classmethod
    def _task(cls, row: dict) -> AgentCommandTask:
        mapping = {
            "taskId": "task_id", "commandId": "command_id", "requestFingerprint": "request_fingerprint",
            "experimentId": "experiment_id", "runId": "run_id", "targetKind": "target_kind", "action": "action",
            "expectedRevision": "expected_revision", "payload": "payload", "requiredCapabilities": "required_capabilities",
            "maxAttempts": "max_attempts", "priority": "priority", "parentTaskId": "parent_task_id", "status": "status",
            "attempts": "attempts", "availableAt": "available_at", "leaseOwner": "lease_owner", "leaseToken": "lease_token",
            "leaseExpiresAt": "lease_expires_at", "heartbeatAt": "heartbeat_at", "resultRevision": "result_revision",
            "resultRunId": "result_run_id", "cancelRequestedAt": "cancel_requested_at", "cancelledAt": "cancelled_at",
            "errorCategory": "error_category", "errorMessage": "error_message", "createdAt": "created_at", "updatedAt": "updated_at",
        }
        values = {target: cls._iso(row.get(source)) for target, source in mapping.items()}
        return AgentCommandTask(**values)

    @staticmethod
    def _worker(row: dict, cutoff: datetime) -> AgentWorkerStatus:
        active = row.get("active_tasks", 0)
        return AgentWorkerStatus(workerId=row["worker_id"], capabilities=row["capabilities"], maxConcurrent=row["max_concurrent"],
            labels=row["labels"], heartbeatAt=row["heartbeat_at"].isoformat(), status="online" if row["heartbeat_at"] >= cutoff else "offline",
            activeTasks=active, availableSlots=max(0, row["max_concurrent"] - active))
