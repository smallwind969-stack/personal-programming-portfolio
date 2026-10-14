from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from threading import RLock
import sqlite3
from uuid import uuid4

from app.schemas.agent_commands import AgentCommandCreate, AgentCommandTask, AgentWorkerStatus


class AgentCommandConflictError(RuntimeError):
    pass


class AgentCommandNotFoundError(LookupError):
    pass


class AgentLeaseConflictError(RuntimeError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SqliteAgentCommandQueue:
    def __init__(self, path: str | Path = ":memory:", clock: Callable[[], datetime] = _utcnow, max_active_per_experiment: int = 1) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._clock = clock
        self._lock = RLock()
        self.maxActivePerExperiment = max_active_per_experiment
        self._connection = sqlite3.connect(self.path, check_same_thread=False, timeout=10, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=FULL")
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_command_tasks (
                task_id TEXT PRIMARY KEY, command_id TEXT UNIQUE NOT NULL, request_fingerprint TEXT NOT NULL,
                experiment_id TEXT NOT NULL, run_id TEXT NOT NULL, target_kind TEXT NOT NULL DEFAULT 'dataAnalysis', action TEXT NOT NULL,
                expected_revision INTEGER NOT NULL, payload_json TEXT NOT NULL, max_attempts INTEGER NOT NULL,
                status TEXT NOT NULL, attempts INTEGER NOT NULL, available_at TEXT NOT NULL,
                lease_owner TEXT, lease_token TEXT, lease_expires_at TEXT, heartbeat_at TEXT,
                priority INTEGER NOT NULL DEFAULT 0, parent_task_id TEXT, result_revision INTEGER, result_run_id TEXT,
                cancel_requested_at TEXT, cancelled_at TEXT, error_category TEXT, error_message TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
            """
        )
        self._ensure_columns()
        self._connection.execute(
            """CREATE TABLE IF NOT EXISTS agent_workers (
            worker_id TEXT PRIMARY KEY, capabilities_json TEXT NOT NULL, max_concurrent INTEGER NOT NULL,
            labels_json TEXT NOT NULL, heartbeat_at TEXT NOT NULL)"""
        )
        self._connection.execute("CREATE INDEX IF NOT EXISTS idx_agent_tasks_claim ON agent_command_tasks(status, available_at, lease_expires_at, created_at)")

    def reset(self) -> None:
        with self._lock:
            self._connection.execute("DELETE FROM agent_command_tasks")
            self._connection.execute("DELETE FROM agent_workers")

    def _ensure_columns(self) -> None:
        existing = {row[1] for row in self._connection.execute("PRAGMA table_info(agent_command_tasks)")}
        additions = {
            "target_kind": "TEXT NOT NULL DEFAULT 'dataAnalysis'", "priority": "INTEGER NOT NULL DEFAULT 0",
            "parent_task_id": "TEXT", "result_run_id": "TEXT", "cancel_requested_at": "TEXT", "cancelled_at": "TEXT",
            "required_capabilities_json": "TEXT NOT NULL DEFAULT '[\"cpu\"]'",
        }
        for name, definition in additions.items():
            if name not in existing: self._connection.execute(f"ALTER TABLE agent_command_tasks ADD COLUMN {name} {definition}")

    def enqueue(self, request: AgentCommandCreate) -> AgentCommandTask:
        canonical = json.dumps(request.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        fingerprint = f"sha256:{sha256(canonical.encode('utf-8')).hexdigest()}"
        now = self._iso(self._clock())
        with self._lock:
            existing = self._connection.execute("SELECT * FROM agent_command_tasks WHERE command_id=?", (request.commandId,)).fetchone()
            if existing:
                if existing["request_fingerprint"] != fingerprint:
                    raise AgentCommandConflictError("commandId has already been used with a different request")
                return self._row(existing)
            task_id = f"agent-task-{uuid4().hex[:12]}"
            values = (
                task_id, request.commandId, fingerprint, request.experimentId, request.runId, request.targetKind, request.action,
                request.expectedRevision, json.dumps(request.payload, ensure_ascii=False, sort_keys=True), request.maxAttempts,
                "queued", 0, now, request.priority, request.parentTaskId, json.dumps(sorted(set(request.requiredCapabilities))), now, now,
            )
            self._connection.execute(
                """INSERT INTO agent_command_tasks
                (task_id, command_id, request_fingerprint, experiment_id, run_id, target_kind, action, expected_revision,
                 payload_json, max_attempts, status, attempts, available_at, priority, parent_task_id, required_capabilities_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", values,
            )
            return self.get(task_id)

    def claim(self, worker_id: str, lease_seconds: int = 30, capabilities: set[str] | None = None) -> AgentCommandTask | None:
        if not worker_id or lease_seconds < 1:
            raise ValueError("worker_id and positive lease_seconds are required")
        now_dt = self._clock(); now = self._iso(now_dt)
        with self._transaction():
            self._connection.execute(
                """UPDATE agent_command_tasks SET status='deadLetter', error_category='leaseExpired',
                error_message='lease expired after maximum attempts', lease_owner=NULL, lease_token=NULL,
                lease_expires_at=NULL, updated_at=?
                WHERE status='leased' AND lease_expires_at<=? AND attempts>=max_attempts""", (now, now),
            )
            rows = self._connection.execute(
                """SELECT * FROM agent_command_tasks
                WHERE attempts < max_attempts AND ((status='queued' AND available_at<=?) OR (status='leased' AND lease_expires_at<=?))
                AND (SELECT COUNT(*) FROM agent_command_tasks active WHERE active.experiment_id=agent_command_tasks.experiment_id
                     AND active.status='leased' AND active.lease_expires_at>?) < ?
                AND (SELECT COUNT(*) FROM agent_command_tasks owned WHERE owned.status='leased' AND owned.lease_owner=?
                     AND owned.lease_expires_at>?) < COALESCE((SELECT max_concurrent FROM agent_workers WHERE worker_id=?), 1000000)
                ORDER BY priority DESC, created_at, task_id""", (now, now, now, self.maxActivePerExperiment, worker_id, now, worker_id),
            ).fetchall()
            row = next((candidate for candidate in rows if capabilities is None or set(json.loads(candidate["required_capabilities_json"])).issubset(capabilities)), None)
            if row is None:
                return None
            token = f"lease-{uuid4().hex}"
            expires = self._iso(now_dt + timedelta(seconds=lease_seconds))
            self._connection.execute(
                """UPDATE agent_command_tasks SET status='leased', attempts=attempts+1, lease_owner=?, lease_token=?,
                lease_expires_at=?, heartbeat_at=?, error_category=NULL, error_message=NULL, updated_at=? WHERE task_id=?""",
                (worker_id, token, expires, now, now, row["task_id"]),
            )
            return self._row(self._connection.execute("SELECT * FROM agent_command_tasks WHERE task_id=?", (row["task_id"],)).fetchone())

    def heartbeat(self, task_id: str, worker_id: str, lease_token: str, lease_seconds: int = 30) -> AgentCommandTask:
        now_dt = self._clock(); now = self._iso(now_dt)
        with self._transaction():
            self._assert_lease(task_id, worker_id, lease_token, now)
            self._connection.execute(
                "UPDATE agent_command_tasks SET heartbeat_at=?, lease_expires_at=?, updated_at=? WHERE task_id=?",
                (now, self._iso(now_dt + timedelta(seconds=lease_seconds)), now, task_id),
            )
            return self.get(task_id)

    def complete(self, task_id: str, worker_id: str, lease_token: str, result_revision: int, result_run_id: str | None = None) -> AgentCommandTask:
        now = self._iso(self._clock())
        with self._transaction():
            self._assert_lease(task_id, worker_id, lease_token, now)
            self._connection.execute(
                """UPDATE agent_command_tasks SET status='completed', result_revision=?, result_run_id=?, lease_owner=NULL,
                lease_token=NULL, lease_expires_at=NULL, updated_at=? WHERE task_id=?""", (result_revision, result_run_id, now, task_id),
            )
            return self.get(task_id)

    def fail(self, task_id: str, worker_id: str, lease_token: str, category: str, message: str, retryable: bool, delay_seconds: int = 0) -> AgentCommandTask:
        now_dt = self._clock(); now = self._iso(now_dt)
        with self._transaction():
            row = self._assert_lease(task_id, worker_id, lease_token, now)
            retry = retryable and row["attempts"] < row["max_attempts"]
            status = "queued" if retry else "deadLetter"
            available = self._iso(now_dt + timedelta(seconds=max(0, delay_seconds)))
            self._connection.execute(
                """UPDATE agent_command_tasks SET status=?, available_at=?, lease_owner=NULL, lease_token=NULL,
                lease_expires_at=NULL, error_category=?, error_message=?, updated_at=? WHERE task_id=?""",
                (status, available, category, message[:2000], now, task_id),
            )
            return self.get(task_id)

    def get(self, task_id: str) -> AgentCommandTask:
        with self._lock:
            row = self._connection.execute("SELECT * FROM agent_command_tasks WHERE task_id=?", (task_id,)).fetchone()
            if row is None:
                raise AgentCommandNotFoundError(task_id)
            return self._row(row)

    def list_recent(self, limit: int = 50, experiment_id: str | None = None) -> list[AgentCommandTask]:
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        sql = "SELECT * FROM agent_command_tasks"
        parameters: tuple = ()
        if experiment_id:
            sql += " WHERE experiment_id=?"
            parameters = (experiment_id,)
        sql += " ORDER BY created_at DESC, task_id DESC LIMIT ?"
        parameters = (*parameters, limit)
        with self._lock:
            rows = self._connection.execute(sql, parameters).fetchall()
        return [self._row(row) for row in rows]

    def cancel(self, task_id: str, reason: str) -> AgentCommandTask:
        now = self._iso(self._clock())
        with self._transaction():
            row = self._connection.execute("SELECT * FROM agent_command_tasks WHERE task_id=?", (task_id,)).fetchone()
            if row is None: raise AgentCommandNotFoundError(task_id)
            if row["status"] == "queued":
                self._connection.execute("UPDATE agent_command_tasks SET status='cancelled', cancelled_at=?, error_category='cancelled', error_message=?, updated_at=? WHERE task_id=?", (now, reason, now, task_id))
            elif row["status"] == "leased":
                self._connection.execute("UPDATE agent_command_tasks SET cancel_requested_at=?, error_category='cancelRequested', error_message=?, updated_at=? WHERE task_id=?", (now, reason, now, task_id))
            else: raise AgentCommandConflictError(f"task in {row['status']} state cannot be cancelled")
            return self.get(task_id)

    def replay(self, task_id: str, command_id: str) -> AgentCommandTask:
        source = self.get(task_id)
        if source.status != "deadLetter": raise AgentCommandConflictError("only a dead-letter task can be replayed")
        return self.enqueue(AgentCommandCreate(
            commandId=command_id, experimentId=source.experimentId, runId=source.runId,
            targetKind=source.targetKind, action=source.action, expectedRevision=source.expectedRevision,
            payload=source.payload, maxAttempts=source.maxAttempts, priority=source.priority, parentTaskId=source.taskId,
        ))

    def acknowledge_cancel(self, task_id: str, worker_id: str, lease_token: str) -> AgentCommandTask:
        now = self._iso(self._clock())
        with self._transaction():
            row = self._assert_lease(task_id, worker_id, lease_token, now)
            if not row["cancel_requested_at"]:
                raise AgentCommandConflictError("task has no cancellation request")
            self._connection.execute("""UPDATE agent_command_tasks SET status='cancelled', cancelled_at=?,
                lease_owner=NULL, lease_token=NULL, lease_expires_at=NULL, updated_at=? WHERE task_id=?""", (now, now, task_id))
            return self.get(task_id)

    def counts(self) -> dict[str, int]:
        result = {key: 0 for key in ("queued", "leased", "completed", "failed", "deadLetter", "cancelled")}
        with self._lock:
            for row in self._connection.execute("SELECT status, COUNT(*) AS count FROM agent_command_tasks GROUP BY status"):
                result[row["status"]] = row["count"]
        return result

    def register_worker(self, worker_id: str, capabilities: set[str], max_concurrent: int = 1, labels: dict[str, str] | None = None) -> AgentWorkerStatus:
        if not worker_id or not capabilities or max_concurrent < 1:
            raise ValueError("worker_id, capabilities and positive max_concurrent are required")
        now = self._iso(self._clock())
        with self._lock:
            self._connection.execute(
                """INSERT INTO agent_workers(worker_id, capabilities_json, max_concurrent, labels_json, heartbeat_at)
                VALUES (?, ?, ?, ?, ?) ON CONFLICT(worker_id) DO UPDATE SET capabilities_json=excluded.capabilities_json,
                max_concurrent=excluded.max_concurrent, labels_json=excluded.labels_json, heartbeat_at=excluded.heartbeat_at""",
                (worker_id, json.dumps(sorted(capabilities)), max_concurrent, json.dumps(labels or {}, sort_keys=True), now),
            )
        return next(item for item in self.worker_status() if item.workerId == worker_id)

    def worker_status(self, stale_after_seconds: int = 60) -> list[AgentWorkerStatus]:
        cutoff = self._clock() - timedelta(seconds=stale_after_seconds)
        with self._lock:
            rows = self._connection.execute("SELECT * FROM agent_workers ORDER BY worker_id").fetchall()
        return [AgentWorkerStatus(
            workerId=row["worker_id"], capabilities=json.loads(row["capabilities_json"]),
            maxConcurrent=row["max_concurrent"], labels=json.loads(row["labels_json"]), heartbeatAt=row["heartbeat_at"],
            status="online" if datetime.fromisoformat(row["heartbeat_at"]) >= cutoff else "offline",
            activeTasks=self._connection.execute("SELECT COUNT(*) FROM agent_command_tasks WHERE status='leased' AND lease_owner=? AND lease_expires_at>?", (row["worker_id"], self._iso(self._clock()))).fetchone()[0],
            availableSlots=max(0, row["max_concurrent"] - self._connection.execute("SELECT COUNT(*) FROM agent_command_tasks WHERE status='leased' AND lease_owner=? AND lease_expires_at>?", (row["worker_id"], self._iso(self._clock()))).fetchone()[0]),
        ) for row in rows]

    def _assert_lease(self, task_id: str, worker_id: str, lease_token: str, now: str) -> sqlite3.Row:
        row = self._connection.execute("SELECT * FROM agent_command_tasks WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            raise AgentCommandNotFoundError(task_id)
        if row["status"] != "leased" or row["lease_owner"] != worker_id or row["lease_token"] != lease_token or row["lease_expires_at"] <= now:
            raise AgentLeaseConflictError("lease is missing, expired, or owned by another worker")
        return row

    class _Transaction:
        def __init__(self, queue: "SqliteAgentCommandQueue") -> None: self.queue = queue
        def __enter__(self):
            self.queue._lock.acquire(); self.queue._connection.execute("BEGIN IMMEDIATE"); return self.queue._connection
        def __exit__(self, exc_type, exc, tb):
            try: self.queue._connection.execute("ROLLBACK" if exc_type else "COMMIT")
            finally: self.queue._lock.release()

    def _transaction(self) -> "SqliteAgentCommandQueue._Transaction":
        return self._Transaction(self)

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _row(row: sqlite3.Row) -> AgentCommandTask:
        return AgentCommandTask(
            taskId=row["task_id"], commandId=row["command_id"], requestFingerprint=row["request_fingerprint"],
            experimentId=row["experiment_id"], runId=row["run_id"], targetKind=row["target_kind"], action=row["action"],
            expectedRevision=row["expected_revision"], payload=json.loads(row["payload_json"]), maxAttempts=row["max_attempts"],
            priority=row["priority"], parentTaskId=row["parent_task_id"],
            requiredCapabilities=json.loads(row["required_capabilities_json"]),
            status=row["status"], attempts=row["attempts"], availableAt=row["available_at"],
            leaseOwner=row["lease_owner"], leaseToken=row["lease_token"], leaseExpiresAt=row["lease_expires_at"],
            heartbeatAt=row["heartbeat_at"], resultRevision=row["result_revision"], resultRunId=row["result_run_id"],
            cancelRequestedAt=row["cancel_requested_at"], cancelledAt=row["cancelled_at"], errorCategory=row["error_category"],
            errorMessage=row["error_message"], createdAt=row["created_at"], updatedAt=row["updated_at"],
        )
