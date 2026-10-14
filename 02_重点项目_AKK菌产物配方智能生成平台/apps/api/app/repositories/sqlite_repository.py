import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SqliteRepository:
    def __init__(self, db_path: str | Path | None = None) -> None:
        default_path = os.getenv("EXPERIMENT_WORKSPACE_DB_PATH") or str(Path(__file__).resolve().parents[4] / "data" / "akk_platform.sqlite3")
        self.db_path = Path(db_path) if db_path is not None else Path(default_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS formula_results (
                    result_id TEXT PRIMARY KEY,
                    candidate_name TEXT NOT NULL,
                    application_name TEXT NOT NULL,
                    approval_status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS experiment_records (
                    experiment_id TEXT PRIMARY KEY,
                    result_id TEXT NOT NULL,
                    sample_code TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    target_range TEXT NOT NULL,
                    status TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    conclusion TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(result_id) REFERENCES formula_results(result_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS experiment_workspaces (
                    experiment_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def save_experiment_workspace(self, workspace: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO experiment_workspaces
                (experiment_id, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    workspace["experimentId"], json.dumps(workspace, ensure_ascii=False),
                    workspace["updatedAt"], workspace["updatedAt"],
                ),
            )
            connection.commit()

    def get_experiment_workspace(self, experiment_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM experiment_workspaces WHERE experiment_id = ?",
                (experiment_id,),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def update_experiment_workspace(self, workspace: dict[str, Any]) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE experiment_workspaces
                SET payload_json = ?, updated_at = ?
                WHERE experiment_id = ?
                """,
                (
                    json.dumps(workspace, ensure_ascii=False),
                    workspace["updatedAt"], workspace["experimentId"],
                ),
            )
            if cursor.rowcount == 0:
                raise LookupError("persisted experiment workspace was not found")
            connection.commit()

    def list_experiment_workspaces(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM experiment_workspaces ORDER BY created_at DESC"
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def delete_experiment_workspace(self, experiment_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM experiment_workspaces WHERE experiment_id = ?",
                (experiment_id,),
            )
            connection.commit()

    def save_formula_result(self, result: dict[str, Any]) -> None:
        candidate = result["candidates"][0]
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO formula_results
                (result_id, candidate_name, application_name, approval_status, created_at, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    result["resultId"],
                    candidate["candidateName"],
                    result["applicationName"],
                    candidate.get("approvalStatus", "pending_research_review"),
                    result["createdAt"],
                    json.dumps(result, ensure_ascii=False),
                ),
            )
            connection.commit()

    def get_formula_result(self, result_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM formula_results WHERE result_id = ?",
                (result_id,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row["payload_json"])

    def list_formula_results(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM formula_results ORDER BY created_at DESC"
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def save_experiment_records(self, result_id: str, records: list[dict[str, Any]]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute("DELETE FROM experiment_records WHERE result_id = ?", (result_id,))
            for record in records:
                connection.execute(
                    """
                    INSERT INTO experiment_records
                    (experiment_id, result_id, sample_code, test_name, metric_value, unit,
                     target_range, status, risk_level, conclusion, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record["experimentId"],
                        result_id,
                        record["sampleCode"],
                        record["testName"],
                        record["metricValue"],
                        record["unit"],
                        record["targetRange"],
                        record["status"],
                        record["riskLevel"],
                        record["conclusion"],
                        record.get("createdAt", now),
                    ),
                )
            connection.commit()

    def list_experiment_records(self, result_id: str | None = None) -> list[dict[str, Any]]:
        if result_id:
            query = "SELECT * FROM experiment_records WHERE result_id = ? ORDER BY created_at DESC"
            params: tuple[Any, ...] = (result_id,)
        else:
            query = "SELECT * FROM experiment_records ORDER BY created_at DESC"
            params = ()
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]
