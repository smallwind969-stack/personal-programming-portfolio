from __future__ import annotations

from pathlib import Path
import sqlite3
from threading import RLock

from app.product_innovation.contracts import ProductInnovationRun, ProductRequirementVersion


class SqliteProductInnovationStore:
    """Durable ledger for innovation runs and immutable confirmed requirements."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("""CREATE TABLE IF NOT EXISTS product_innovation_runs (
                run_id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL, command_id TEXT NOT NULL,
                created_at TEXT NOT NULL, payload_json TEXT NOT NULL,
                UNIQUE(experiment_id, command_id))""")
            connection.execute("""CREATE TABLE IF NOT EXISTS product_requirement_versions (
                requirement_version_id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL,
                version INTEGER NOT NULL, source_run_id TEXT NOT NULL,
                confirmation_command_id TEXT NOT NULL, confirmed_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                UNIQUE(experiment_id, version), UNIQUE(experiment_id, confirmation_command_id),
                UNIQUE(source_run_id))""")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    def save_run(self, run: ProductInnovationRun) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("""INSERT INTO product_innovation_runs
                (run_id, experiment_id, command_id, created_at, payload_json) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET payload_json=excluded.payload_json""",
                (run.runId, run.experimentId, run.commandId, run.createdAt, run.model_dump_json()))

    def load_runs(self) -> list[ProductInnovationRun]:
        with self._lock, self._connect() as connection:
            rows = connection.execute("SELECT payload_json FROM product_innovation_runs ORDER BY created_at, run_id").fetchall()
        return [ProductInnovationRun.model_validate_json(row[0]) for row in rows]

    def save_requirement(self, version: ProductRequirementVersion) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("""INSERT INTO product_requirement_versions
                (requirement_version_id, experiment_id, version, source_run_id,
                 confirmation_command_id, confirmed_at, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(requirement_version_id) DO UPDATE SET payload_json=excluded.payload_json""",
                (version.requirementVersionId, version.experimentId, version.version, version.sourceRunId,
                 version.confirmationCommandId, version.confirmedAt, version.model_dump_json()))

    def load_requirements(self) -> list[ProductRequirementVersion]:
        with self._lock, self._connect() as connection:
            rows = connection.execute("SELECT payload_json FROM product_requirement_versions ORDER BY experiment_id, version").fetchall()
        return [ProductRequirementVersion.model_validate_json(row[0]) for row in rows]

    def reset(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM product_requirement_versions")
            connection.execute("DELETE FROM product_innovation_runs")
