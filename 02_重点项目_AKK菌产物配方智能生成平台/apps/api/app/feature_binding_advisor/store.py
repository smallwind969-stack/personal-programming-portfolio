from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock

from app.feature_binding_advisor.contracts import FeatureBindingSuggestionRun


class SqliteFeatureBindingSuggestionStore:
    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = RLock()
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS feature_binding_suggestion_runs (
                run_id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                command_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                UNIQUE(experiment_id, model_version, command_id)
            )
            """
        )
        self._connection.commit()

    def save(self, run: FeatureBindingSuggestionRun) -> FeatureBindingSuggestionRun:
        payload = json.dumps(run.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            self._connection.execute(
                "INSERT OR IGNORE INTO feature_binding_suggestion_runs "
                "(run_id, experiment_id, model_version, command_id, payload) VALUES (?, ?, ?, ?, ?)",
                (run.runId, run.experimentId, run.modelVersion, run.commandId, payload),
            )
            self._connection.commit()
            return self.get_by_command(run.experimentId, run.modelVersion, run.commandId) or run

    def get(self, experiment_id: str, run_id: str) -> FeatureBindingSuggestionRun | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload FROM feature_binding_suggestion_runs WHERE experiment_id = ? AND run_id = ?",
                (experiment_id, run_id),
            ).fetchone()
        return FeatureBindingSuggestionRun.model_validate_json(row[0]) if row else None

    def get_by_command(
        self, experiment_id: str, model_version: str, command_id: str,
    ) -> FeatureBindingSuggestionRun | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload FROM feature_binding_suggestion_runs "
                "WHERE experiment_id = ? AND model_version = ? AND command_id = ?",
                (experiment_id, model_version, command_id),
            ).fetchone()
        return FeatureBindingSuggestionRun.model_validate_json(row[0]) if row else None
