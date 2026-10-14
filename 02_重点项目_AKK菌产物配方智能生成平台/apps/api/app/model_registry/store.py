from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from app.model_registry.contracts import PromotedModelRecord


class SqlitePromotedModelRegistry:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS promoted_models (
                experiment_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                trial_id TEXT NOT NULL,
                approved_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (experiment_id, model_version)
            )
        """)
        self._connection.commit()

    def register(self, record: PromotedModelRecord) -> PromotedModelRecord:
        existing = self.get(record.experimentId, record.modelVersion)
        if existing:
            if existing.model_dump(mode="json") != record.model_dump(mode="json"):
                raise ValueError("model version is already registered with different lineage")
            return existing
        self._connection.execute(
            "INSERT INTO promoted_models (experiment_id, model_version, trial_id, approved_at, payload_json) VALUES (?, ?, ?, ?, ?)",
            (record.experimentId, record.modelVersion, record.trialId, record.approvedAt,
             json.dumps(record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)),
        )
        self._connection.commit()
        return record

    def get(self, experiment_id: str, model_version: str) -> PromotedModelRecord | None:
        row = self._connection.execute(
            "SELECT payload_json FROM promoted_models WHERE experiment_id = ? AND model_version = ?",
            (experiment_id, model_version),
        ).fetchone()
        return PromotedModelRecord.model_validate_json(row["payload_json"]) if row else None

    def latest(self, experiment_id: str) -> PromotedModelRecord | None:
        row = self._connection.execute(
            "SELECT payload_json FROM promoted_models WHERE experiment_id = ? ORDER BY approved_at DESC, model_version DESC LIMIT 1",
            (experiment_id,),
        ).fetchone()
        return PromotedModelRecord.model_validate_json(row["payload_json"]) if row else None

    def list(self, experiment_id: str) -> list[PromotedModelRecord]:
        rows = self._connection.execute(
            "SELECT payload_json FROM promoted_models WHERE experiment_id = ? ORDER BY approved_at DESC, model_version DESC",
            (experiment_id,),
        ).fetchall()
        return [PromotedModelRecord.model_validate_json(row["payload_json"]) for row in rows]

    def latest_by_target(self, experiment_id: str, target_field: str) -> PromotedModelRecord | None:
        return next((record for record in self.list(experiment_id)
                     if record.status == "approved" and record.validationStatus == "passed"
                     and record.active and record.targetField == target_field), None)

    def latest_per_target(self, experiment_id: str) -> list[PromotedModelRecord]:
        latest: dict[str, PromotedModelRecord] = {}
        for record in self.list(experiment_id):
            if (record.status == "approved" and record.validationStatus == "passed"
                    and record.active and record.targetField not in latest):
                latest[record.targetField] = record
        return list(latest.values())
