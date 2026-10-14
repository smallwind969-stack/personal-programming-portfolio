from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from threading import RLock

from app.research.contracts import ResearchCampaign


class SqliteResearchCampaignStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:": Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("""CREATE TABLE IF NOT EXISTS research_campaigns (
            experiment_id TEXT NOT NULL, campaign_id TEXT PRIMARY KEY, create_command_id TEXT NOT NULL,
            payload_json TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(experiment_id, create_command_id))""")

    def save(self, campaign: ResearchCampaign) -> None:
        payload = campaign.model_dump_json()
        with self._lock:
            self._connection.execute("""INSERT INTO research_campaigns(experiment_id,campaign_id,create_command_id,payload_json,updated_at)
                VALUES(?,?,?,?,?) ON CONFLICT(campaign_id) DO UPDATE SET payload_json=excluded.payload_json,updated_at=excluded.updated_at""",
                (campaign.experimentId, campaign.campaignId, campaign.createCommandId, payload, campaign.updatedAt))

    def get(self, experiment_id: str, campaign_id: str) -> ResearchCampaign | None:
        with self._lock:
            row = self._connection.execute("SELECT payload_json FROM research_campaigns WHERE experiment_id=? AND campaign_id=?", (experiment_id, campaign_id)).fetchone()
        return ResearchCampaign.model_validate_json(row["payload_json"]) if row else None

    def by_command(self, experiment_id: str, command_id: str) -> ResearchCampaign | None:
        with self._lock:
            row = self._connection.execute("SELECT payload_json FROM research_campaigns WHERE experiment_id=? AND create_command_id=?", (experiment_id, command_id)).fetchone()
        return ResearchCampaign.model_validate_json(row["payload_json"]) if row else None

    def list(self, experiment_id: str) -> list[ResearchCampaign]:
        with self._lock:
            rows = self._connection.execute("SELECT payload_json FROM research_campaigns WHERE experiment_id=? ORDER BY updated_at DESC", (experiment_id,)).fetchall()
        return [ResearchCampaign.model_validate_json(row["payload_json"]) for row in rows]

    def reset(self) -> None:
        with self._lock: self._connection.execute("DELETE FROM research_campaigns")
