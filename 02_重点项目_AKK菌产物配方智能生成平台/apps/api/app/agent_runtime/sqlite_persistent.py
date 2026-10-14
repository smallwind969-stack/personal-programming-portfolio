from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Callable, TypeVar

from app.agent_runtime.contracts import RuntimeCommand, RuntimeContext, RuntimeGraphDefinition, RuntimeSnapshot
from app.agent_runtime.deterministic import DeterministicRuntimeAdapter


class RuntimeCheckpointError(RuntimeError):
    pass


class SqliteRuntimeCheckpointStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._connect() as connection:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS agent_runtime_checkpoints (
                        run_id TEXT PRIMARY KEY,
                        snapshot_json TEXT NOT NULL,
                        definition_json TEXT NOT NULL,
                        processed_commands_json TEXT NOT NULL,
                        revision INTEGER NOT NULL,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
        except sqlite3.Error as exc:
            raise RuntimeCheckpointError(f"checkpoint initialization failed: {exc}") from exc

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.path), timeout=10)

    def save(self, snapshot: RuntimeSnapshot, definition: RuntimeGraphDefinition, command_ids: set[str]) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO agent_runtime_checkpoints
                        (run_id, snapshot_json, definition_json, processed_commands_json, revision, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(run_id) DO UPDATE SET
                        snapshot_json=excluded.snapshot_json,
                        definition_json=excluded.definition_json,
                        processed_commands_json=excluded.processed_commands_json,
                        revision=excluded.revision,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (
                        snapshot.runId,
                        snapshot.model_dump_json(),
                        definition.model_dump_json(),
                        json.dumps(sorted(command_ids), ensure_ascii=False),
                        snapshot.revision,
                    ),
                )
        except (sqlite3.Error, TypeError, ValueError) as exc:
            raise RuntimeCheckpointError(f"checkpoint commit failed: {exc}") from exc

    def load_all(self) -> list[tuple[RuntimeSnapshot, RuntimeGraphDefinition, set[str]]]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT snapshot_json, definition_json, processed_commands_json FROM agent_runtime_checkpoints ORDER BY updated_at, run_id"
                ).fetchall()
            return [
                (
                    RuntimeSnapshot.model_validate_json(snapshot_json),
                    RuntimeGraphDefinition.model_validate_json(definition_json),
                    set(json.loads(commands_json)),
                )
                for snapshot_json, definition_json, commands_json in rows
            ]
        except Exception as exc:
            raise RuntimeCheckpointError(f"checkpoint load failed: {type(exc).__name__}: {exc}") from exc

    def load_one(self, run_id: str) -> tuple[RuntimeSnapshot, RuntimeGraphDefinition, set[str]] | None:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT snapshot_json, definition_json, processed_commands_json FROM agent_runtime_checkpoints WHERE run_id=?",
                    (run_id,),
                ).fetchone()
            if row is None:
                return None
            return RuntimeSnapshot.model_validate_json(row[0]), RuntimeGraphDefinition.model_validate_json(row[1]), set(json.loads(row[2]))
        except Exception as exc:
            raise RuntimeCheckpointError(f"checkpoint load failed: {type(exc).__name__}: {exc}") from exc


T = TypeVar("T")


class PersistentRuntimeAdapter(DeterministicRuntimeAdapter):
    """Deterministic state graph with crash-safe SQLite snapshots."""

    def __init__(self, path: str | Path) -> None:
        super().__init__()
        self._store = SqliteRuntimeCheckpointStore(path)
        for snapshot, definition, commands in self._store.load_all():
            if snapshot.runId in self._runs:
                raise RuntimeCheckpointError(f"checkpoint load failed: duplicate run {snapshot.runId}")
            self._runs[snapshot.runId] = snapshot
            self._definitions[snapshot.runId] = definition
            self._processed_commands[snapshot.runId] = commands

    def start(self, definition: RuntimeGraphDefinition, initial_state: dict, context: RuntimeContext) -> RuntimeSnapshot:
        result = super().start(definition, initial_state, context)
        try:
            self._persist(result.runId)
        except Exception as exc:
            self._runs.pop(result.runId, None)
            self._definitions.pop(result.runId, None)
            self._processed_commands.pop(result.runId, None)
            if isinstance(exc, RuntimeCheckpointError):
                raise
            raise RuntimeCheckpointError(f"checkpoint commit failed: {exc}") from exc
        return result

    def advance(self, run_id: str, command: RuntimeCommand) -> RuntimeSnapshot:
        return self._mutate(run_id, lambda: super(PersistentRuntimeAdapter, self).advance(run_id, command))

    def interrupt(self, run_id: str, reason: str) -> RuntimeSnapshot:
        return self._mutate(run_id, lambda: super(PersistentRuntimeAdapter, self).interrupt(run_id, reason))

    def resume(self, run_id: str, human_decision: dict) -> RuntimeSnapshot:
        return self._mutate(run_id, lambda: super(PersistentRuntimeAdapter, self).resume(run_id, human_decision))

    def patch_state(self, run_id: str, patch: dict, event_type: str, detail: str, expected_revision: int, command_id: str) -> RuntimeSnapshot:
        return self._mutate(
            run_id,
            lambda: super(PersistentRuntimeAdapter, self).patch_state(run_id, patch, event_type, detail, expected_revision, command_id),
        )

    def list_snapshots(self) -> list[RuntimeSnapshot]:
        self.refresh_all()
        with self._lock:
            return [item.model_copy(deep=True) for item in self._runs.values()]

    def get(self, run_id: str) -> RuntimeSnapshot:
        self._refresh_one(run_id)
        return super().get(run_id)

    def refresh_all(self) -> None:
        with self._lock:
            for snapshot, definition, commands in self._store.load_all():
                current = self._runs.get(snapshot.runId)
                if current is None or snapshot.revision > current.revision:
                    self._runs[snapshot.runId] = snapshot
                    self._definitions[snapshot.runId] = definition
                    self._processed_commands[snapshot.runId] = commands

    def _refresh_one(self, run_id: str) -> None:
        with self._lock:
            loaded = self._store.load_one(run_id)
            if loaded is None:
                return
            snapshot, definition, commands = loaded
            current = self._runs.get(run_id)
            if current is None or snapshot.revision > current.revision:
                self._runs[run_id] = snapshot
                self._definitions[run_id] = definition
                self._processed_commands[run_id] = commands

    def _mutate(self, run_id: str, operation: Callable[[], T]) -> T:
        with self._lock:
            before = self._get_mutable(run_id).model_copy(deep=True)
            commands_before = set(self._processed_commands[run_id])
            result = operation()
            try:
                self._persist(run_id)
            except Exception as exc:
                self._runs[run_id] = before
                self._processed_commands[run_id] = commands_before
                if isinstance(exc, RuntimeCheckpointError):
                    raise
                raise RuntimeCheckpointError(f"checkpoint commit failed: {exc}") from exc
            return result

    def _persist(self, run_id: str) -> None:
        self._store.save(self._runs[run_id], self._definitions[run_id], self._processed_commands[run_id])
