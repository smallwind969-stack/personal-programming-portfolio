from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.enterprise_knowledge.contracts import EnterpriseKnowledgeEntry


class EnterpriseKnowledgeUsage(BaseModel):
    usageId: str
    experimentId: str
    knowledgeIds: list[str] = Field(min_length=1)
    sourceEntries: list[EnterpriseKnowledgeEntry] = Field(min_length=1)
    purpose: Literal["modeling", "simulation", "optimization", "reporting"]
    targetVersion: str
    operator: str
    note: str
    usageFingerprint: str
    createdAt: str


class EnterpriseKnowledgeUsageRequest(BaseModel):
    knowledgeIds: list[str] = Field(min_length=1, max_length=100)
    purpose: Literal["modeling", "simulation", "optimization", "reporting"]
    targetVersion: str = Field(min_length=1, max_length=200)
    operator: str = Field(min_length=1, max_length=80)
    note: str = Field(min_length=2, max_length=1000)


class EnterpriseKnowledgeUsageService:
    RECORD_TYPE = "enterprise_knowledge_usage"

    def __init__(self, *, store, knowledge_source) -> None:
        self.store = store
        self.knowledgeSource = knowledge_source

    def register(
        self, experiment_id: str, *, knowledge_ids: list[str], purpose: str,
        target_version: str, operator: str, note: str,
    ) -> EnterpriseKnowledgeUsage:
        unique_ids = list(dict.fromkeys(knowledge_ids))
        if not unique_ids:
            raise ValueError("at least one knowledge entry is required")
        entries = {entry.knowledgeId: entry for entry in self.knowledgeSource.list()}
        missing = sorted(set(unique_ids) - set(entries))
        if missing:
            raise ValueError(f"knowledge entry not found: {', '.join(missing)}")
        source_entries = [entries[item] for item in unique_ids]
        fingerprint = "sha256:" + sha256(json.dumps({
            "experimentId": experiment_id, "knowledgeIds": unique_ids,
            "purpose": purpose, "targetVersion": target_version,
        }, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        usage_id = f"usage-{fingerprint.removeprefix('sha256:')[:16]}"
        existing = self.store.list(self.RECORD_TYPE, experiment_id)
        previous = next((EnterpriseKnowledgeUsage.model_validate(item) for item in existing if item.get("usageFingerprint") == fingerprint), None)
        if previous is not None:
            return previous
        usage = EnterpriseKnowledgeUsage(
            usageId=usage_id, experimentId=experiment_id, knowledgeIds=unique_ids,
            sourceEntries=source_entries, purpose=purpose, targetVersion=target_version,
            operator=operator.strip(), note=note.strip(), usageFingerprint=fingerprint,
            createdAt=datetime.now(timezone.utc).isoformat(),
        )
        self.store.save(self.RECORD_TYPE, usage.usageId, experiment_id, usage.model_dump(mode="json"))
        return usage

    def list(self, *, experiment_id: str | None = None) -> list[EnterpriseKnowledgeUsage]:
        rows = [EnterpriseKnowledgeUsage.model_validate(item) for item in self.store.list(self.RECORD_TYPE, experiment_id)]
        rows.sort(key=lambda item: item.createdAt, reverse=True)
        return rows
