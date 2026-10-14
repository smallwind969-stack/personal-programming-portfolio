from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.model_registry.bindings import is_supported_simulation_parameter


class DeviceAdapterEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sourceFieldAlias: str
    standardField: str
    simulationParameter: str
    sourceUnit: str | None = None
    targetUnit: str | None = None
    scale: float = 1.0
    offset: float = 0.0

    @model_validator(mode="after")
    def validate_entry(self):
        if not is_supported_simulation_parameter(self.simulationParameter):
            raise ValueError(f"unsupported simulation parameter: {self.simulationParameter}")
        if not math.isfinite(self.scale) or not math.isfinite(self.offset) or self.scale == 0:
            raise ValueError("adapter conversion must be finite and scale must be non-zero")
        return self


class DeviceAdapterPackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enterpriseKey: str = Field(min_length=1)
    deviceType: str = Field(min_length=1)
    packVersion: str = Field(min_length=1)
    entries: list[DeviceAdapterEntry] = Field(min_length=1)
    createdBy: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_aliases(self):
        aliases = [entry.sourceFieldAlias.casefold() for entry in self.entries]
        if len(aliases) != len(set(aliases)):
            raise ValueError("adapter pack contains duplicate source aliases")
        return self


class DeviceAdapterPack(DeviceAdapterPackCreate):
    packId: str
    createdAt: str
    integrityScheme: Literal["canonical-json-sha256"] = "canonical-json-sha256"
    contentHash: str


class DeviceAdapterEntryChange(BaseModel):
    sourceFieldAlias: str
    changedFields: list[str]
    before: DeviceAdapterEntry
    after: DeviceAdapterEntry


class DeviceAdapterPackComparison(BaseModel):
    enterpriseKey: str
    deviceType: str
    baseVersion: str
    targetVersion: str
    baseContentHash: str
    targetContentHash: str
    added: list[DeviceAdapterEntry]
    removed: list[DeviceAdapterEntry]
    changed: list[DeviceAdapterEntryChange]
    unchangedCount: int


def _content_hash(payload: dict) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "contentHash"}
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return "sha256:" + sha256(canonical).hexdigest()


class SqliteDeviceAdapterPackStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:": Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock(); self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("""CREATE TABLE IF NOT EXISTS device_adapter_packs (
            enterprise_key TEXT NOT NULL, device_type TEXT NOT NULL, pack_version TEXT NOT NULL,
            payload_json TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(enterprise_key, device_type, pack_version))""")
        self._connection.commit()

    def get(self, enterprise_key: str, device_type: str, pack_version: str) -> DeviceAdapterPack | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload_json FROM device_adapter_packs WHERE enterprise_key=? AND device_type=? AND pack_version=?",
                (enterprise_key, device_type, pack_version),
            ).fetchone()
        return DeviceAdapterPack.model_validate_json(row["payload_json"]) if row else None

    def save(self, pack: DeviceAdapterPack) -> DeviceAdapterPack:
        existing = self.get(pack.enterpriseKey, pack.deviceType, pack.packVersion)
        if existing:
            if existing.contentHash != pack.contentHash:
                raise ValueError("adapter pack version already exists with different content")
            return existing
        with self._lock:
            self._connection.execute("INSERT INTO device_adapter_packs VALUES (?, ?, ?, ?, ?)", (
                pack.enterpriseKey, pack.deviceType, pack.packVersion, pack.model_dump_json(), pack.createdAt,
            )); self._connection.commit()
        return pack

    def list(self, enterprise_key: str | None = None) -> list[DeviceAdapterPack]:
        with self._lock:
            if enterprise_key:
                rows = self._connection.execute("SELECT payload_json FROM device_adapter_packs WHERE enterprise_key=? ORDER BY created_at DESC", (enterprise_key,)).fetchall()
            else:
                rows = self._connection.execute("SELECT payload_json FROM device_adapter_packs ORDER BY created_at DESC").fetchall()
        return [DeviceAdapterPack.model_validate_json(row["payload_json"]) for row in rows]


class DeviceAdapterPackService:
    def __init__(self, store: SqliteDeviceAdapterPackStore) -> None:
        self.store = store

    def export(self, request: DeviceAdapterPackCreate) -> DeviceAdapterPack:
        existing = self.store.get(request.enterpriseKey, request.deviceType, request.packVersion)
        if existing:
            semantic = DeviceAdapterPackCreate(
                enterpriseKey=existing.enterpriseKey, deviceType=existing.deviceType,
                packVersion=existing.packVersion, entries=existing.entries, createdBy=existing.createdBy,
            ).model_dump(mode="json")
            if semantic != request.model_dump(mode="json"):
                raise ValueError("adapter pack version already exists with different content")
            return existing
        base = {
            **request.model_dump(mode="json"),
            "packId": f"adapter-{request.enterpriseKey}-{request.deviceType}-{request.packVersion}",
            "createdAt": datetime.now(timezone.utc).isoformat(), "integrityScheme": "canonical-json-sha256",
        }
        return self.store.save(DeviceAdapterPack(**base, contentHash=_content_hash(base)))

    def import_pack(self, payload: dict) -> DeviceAdapterPack:
        pack = DeviceAdapterPack.model_validate(payload)
        if pack.contentHash != _content_hash(pack.model_dump(mode="json")):
            raise ValueError("adapter pack integrity verification failed")
        return self.store.save(pack)

    def get_verified(
        self, enterprise_key: str, device_type: str, pack_version: str,
    ) -> DeviceAdapterPack | None:
        pack = self.store.get(enterprise_key, device_type, pack_version)
        if pack is None:
            return None
        if pack.contentHash != _content_hash(pack.model_dump(mode="json")):
            raise ValueError("adapter pack integrity verification failed")
        return pack

    def compare(
        self, enterprise_key: str, device_type: str,
        base_version: str, target_version: str,
    ) -> DeviceAdapterPackComparison:
        if base_version == target_version:
            raise ValueError("adapter pack comparison requires different versions")
        base = self.get_verified(enterprise_key, device_type, base_version)
        target = self.get_verified(enterprise_key, device_type, target_version)
        if base is None or target is None:
            raise LookupError("device adapter pack version was not found")
        base_entries = {entry.sourceFieldAlias.casefold(): entry for entry in base.entries}
        target_entries = {entry.sourceFieldAlias.casefold(): entry for entry in target.entries}
        added = [target_entries[key] for key in sorted(target_entries.keys() - base_entries.keys())]
        removed = [base_entries[key] for key in sorted(base_entries.keys() - target_entries.keys())]
        changed: list[DeviceAdapterEntryChange] = []
        unchanged = 0
        comparable_fields = [
            "standardField", "simulationParameter", "sourceUnit", "targetUnit", "scale", "offset",
        ]
        for key in sorted(base_entries.keys() & target_entries.keys()):
            before = base_entries[key]
            after = target_entries[key]
            changed_fields = [
                field for field in comparable_fields
                if getattr(before, field) != getattr(after, field)
            ]
            if changed_fields:
                changed.append(DeviceAdapterEntryChange(
                    sourceFieldAlias=after.sourceFieldAlias,
                    changedFields=changed_fields, before=before, after=after,
                ))
            else:
                unchanged += 1
        return DeviceAdapterPackComparison(
            enterpriseKey=enterprise_key, deviceType=device_type,
            baseVersion=base_version, targetVersion=target_version,
            baseContentHash=base.contentHash, targetContentHash=target.contentHash,
            added=added, removed=removed, changed=changed, unchangedCount=unchanged,
        )
