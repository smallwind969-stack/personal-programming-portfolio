from __future__ import annotations

from pathlib import Path
import sqlite3
from threading import RLock
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class SqliteDomainRunStore(Generic[T]):
    def __init__(self, path: str | Path, namespace: str, model: type[T]) -> None:
        self.path, self.namespace, self.model = str(path), namespace, model
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("""CREATE TABLE IF NOT EXISTS domain_runs (
                namespace TEXT NOT NULL, run_id TEXT NOT NULL, experiment_id TEXT NOT NULL,
                version INTEGER NOT NULL, payload_json TEXT NOT NULL, updated_at TEXT NOT NULL,
                PRIMARY KEY(namespace, run_id))""")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    def save(self, run: T) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("""INSERT INTO domain_runs(namespace, run_id, experiment_id, version, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(namespace, run_id) DO UPDATE SET
                experiment_id=excluded.experiment_id, version=excluded.version,
                payload_json=excluded.payload_json, updated_at=excluded.updated_at""",
                (self.namespace, run.runId, run.experimentId, run.version, run.model_dump_json(), run.updatedAt))

    def load_all(self) -> list[T]:
        with self._lock, self._connect() as connection:
            rows = connection.execute("SELECT payload_json FROM domain_runs WHERE namespace=? ORDER BY experiment_id, version, run_id", (self.namespace,)).fetchall()
        return [self.model.model_validate_json(row[0]) for row in rows]

    def reset(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM domain_runs WHERE namespace=?", (self.namespace,))
