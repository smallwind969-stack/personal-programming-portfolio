from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from threading import RLock
from uuid import uuid4


class SqliteExperimentDataStore:
    """Persistent metadata records plus immutable content-addressed raw objects."""

    def __init__(self, db_path: str | Path, object_root: str | Path) -> None:
        self.db_path = Path(db_path)
        self.object_root = Path(object_root)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.object_root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS experiment_data_records (
                    record_type TEXT NOT NULL,
                    record_key TEXT NOT NULL,
                    experiment_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    deleted_at TEXT,
                    PRIMARY KEY (record_type, record_key)
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_experiment_data_records_lookup
                ON experiment_data_records(record_type, experiment_id, deleted_at)
            """)
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def save(self, record_type: str, record_key: str, experiment_id: str, payload: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        with self._lock, self._connect() as connection:
            connection.execute("""
                INSERT INTO experiment_data_records
                    (record_type, record_key, experiment_id, payload_json, updated_at, deleted_at)
                VALUES (?, ?, ?, ?, ?, NULL)
                ON CONFLICT(record_type, record_key) DO UPDATE SET
                    experiment_id=excluded.experiment_id,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at,
                    deleted_at=NULL
            """, (record_type, record_key, experiment_id, encoded, now))
            connection.commit()

    def get(self, record_type: str, record_key: str, include_deleted: bool = False) -> dict | None:
        deleted_clause = "" if include_deleted else " AND deleted_at IS NULL"
        with self._lock, self._connect() as connection:
            row = connection.execute(
                f"SELECT payload_json FROM experiment_data_records WHERE record_type=? AND record_key=?{deleted_clause}",
                (record_type, record_key),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list(self, record_type: str, experiment_id: str | None = None) -> list[dict]:
        query = "SELECT payload_json FROM experiment_data_records WHERE record_type=? AND deleted_at IS NULL"
        params: list[str] = [record_type]
        if experiment_id is not None:
            query += " AND experiment_id=?"
            params.append(experiment_id)
        query += " ORDER BY updated_at ASC"
        with self._lock, self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def soft_delete(self, record_type: str, record_key: str) -> None:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "UPDATE experiment_data_records SET deleted_at=?, updated_at=? WHERE record_type=? AND record_key=? AND deleted_at IS NULL",
                (
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                    record_type, record_key,
                ),
            )
            if cursor.rowcount == 0:
                raise LookupError("persistent data record was not found")
            connection.commit()

    def object_path(self, content_hash: str) -> Path:
        normalized = content_hash.removeprefix("sha256:")
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError("invalid SHA-256 content hash")
        return self.object_root / "sha256" / normalized[:2] / f"{normalized}.txt"

    def put_content(self, content: str, expected_hash: str) -> Path:
        return self.put_bytes(content.encode("utf-8"), expected_hash)

    def put_bytes(self, content: bytes, expected_hash: str) -> Path:
        actual = sha256(content).hexdigest()
        normalized = expected_hash.removeprefix("sha256:")
        if actual != normalized:
            raise ValueError("raw asset integrity verification failed before storage")
        target = self.object_path(normalized)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            self.read_verified(normalized)
            return target
        temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
        temporary.write_bytes(content)
        temporary.replace(target)
        return target

    def read_verified(self, content_hash: str) -> str:
        return self.read_verified_bytes(content_hash).decode("utf-8")

    def read_verified_bytes(self, content_hash: str) -> bytes:
        normalized = content_hash.removeprefix("sha256:")
        path = self.object_path(normalized)
        if not path.exists():
            raise ValueError("raw asset integrity verification failed: object is missing")
        content = path.read_bytes()
        if sha256(content).hexdigest() != normalized:
            raise ValueError("raw asset integrity verification failed: hash mismatch")
        return content
