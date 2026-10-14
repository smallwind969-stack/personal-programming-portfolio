from __future__ import annotations

import math
import re
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from app.feature_binding_advisor.contracts import DeviceAdapterPackReference


SUPPORTED_SIMULATION_PARAMETERS = {
    "carbonConcentration", "cultureHours", "temperatureC", "ph", "anaerobicScore",
    "pressureMpa", "stirringRpm",
}


def is_supported_simulation_parameter(value: str) -> bool:
    """Allow built-ins plus dictionary-issued custom keys; arbitrary controls stay rejected."""
    return value in SUPPORTED_SIMULATION_PARAMETERS or bool(re.fullmatch(r"custom_[1-9][0-9]*", value))


class FeatureBindingEntry(BaseModel):
    modelFeature: str
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
            raise ValueError("binding scale and offset must be finite and scale must be non-zero")
        return self


class FeatureBindingVersion(BaseModel):
    bindingVersion: str
    experimentId: str
    modelVersion: str
    featureNames: list[str] = Field(min_length=1)
    entries: list[FeatureBindingEntry] = Field(min_length=1)
    confirmedBy: str = Field(min_length=1)
    confirmationReason: str = Field(min_length=2)
    suggestionRunId: str | None = None
    adapterPack: DeviceAdapterPackReference | None = None
    createdAt: str
    status: Literal["confirmed"] = "confirmed"

    @model_validator(mode="after")
    def validate_coverage(self):
        bound = [entry.modelFeature for entry in self.entries]
        if len(bound) != len(set(bound)) or set(bound) != set(self.featureNames) or len(bound) != len(self.featureNames):
            raise ValueError("binding entries must exactly cover unique model feature names")
        return self


class FeatureBindingConfirmRequest(BaseModel):
    bindingVersion: str
    modelVersion: str
    featureNames: list[str] = Field(min_length=1)
    entries: list[FeatureBindingEntry] = Field(min_length=1)
    confirmedBy: str = Field(min_length=1)
    confirmationReason: str = Field(min_length=2)
    suggestionRunId: str | None = None
    adapterPack: DeviceAdapterPackReference | None = None


class FeatureBindingAudit(BaseModel):
    modelFeature: str
    standardField: str
    simulationParameter: str
    sourceUnit: str | None = None
    targetUnit: str | None = None
    sourceValue: float
    modelValue: float
    scale: float
    offset: float


class BoundModelInput(BaseModel):
    experimentId: str
    modelVersion: str
    bindingVersion: str
    suggestionRunId: str | None = None
    adapterPack: DeviceAdapterPackReference | None = None
    modelInputs: dict[str, float]
    audit: list[FeatureBindingAudit]


class SqliteFeatureBindingStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:": Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS feature_bindings (
                experiment_id TEXT NOT NULL, model_version TEXT NOT NULL, binding_version TEXT NOT NULL,
                created_at TEXT NOT NULL, payload_json TEXT NOT NULL,
                PRIMARY KEY (experiment_id, model_version, binding_version)
            )
        """)
        self._connection.commit()

    def save(self, binding: FeatureBindingVersion) -> FeatureBindingVersion:
        existing = self.get(binding.experimentId, binding.modelVersion, binding.bindingVersion)
        if existing:
            if existing.model_dump(mode="json") != binding.model_dump(mode="json"):
                raise ValueError("binding version is already registered with different binding lineage")
            return existing
        payload = binding.model_dump_json()
        with self._lock:
            self._connection.execute(
                "INSERT INTO feature_bindings VALUES (?, ?, ?, ?, ?)",
                (binding.experimentId, binding.modelVersion, binding.bindingVersion, binding.createdAt, payload),
            )
            self._connection.commit()
        return binding

    def get(self, experiment_id: str, model_version: str, binding_version: str) -> FeatureBindingVersion | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload_json FROM feature_bindings WHERE experiment_id=? AND model_version=? AND binding_version=?",
                (experiment_id, model_version, binding_version),
            ).fetchone()
        return FeatureBindingVersion.model_validate_json(row["payload_json"]) if row else None

    def latest(self, experiment_id: str, model_version: str) -> FeatureBindingVersion | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload_json FROM feature_bindings WHERE experiment_id=? AND model_version=? ORDER BY created_at DESC, binding_version DESC LIMIT 1",
                (experiment_id, model_version),
            ).fetchone()
        return FeatureBindingVersion.model_validate_json(row["payload_json"]) if row else None


class SimulationFeatureBindingService:
    def __init__(self, store: SqliteFeatureBindingStore) -> None:
        self.store = store

    def confirm(self, binding: FeatureBindingVersion) -> FeatureBindingVersion:
        return self.store.save(binding)

    def bind(self, experiment_id: str, model_version: str, parameters: dict,
             binding_version: str | None = None) -> BoundModelInput:
        binding = self.store.get(experiment_id, model_version, binding_version) if binding_version else self.store.latest(experiment_id, model_version)
        if binding is None:
            raise LookupError("no confirmed feature binding exists for this model")
        values: dict[str, float] = {}; audit: list[FeatureBindingAudit] = []
        for entry in binding.entries:
            if entry.simulationParameter not in parameters:
                raise ValueError(f"missing simulation parameter: {entry.simulationParameter}")
            raw = parameters[entry.simulationParameter]
            if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(float(raw)):
                raise ValueError(f"simulation parameter {entry.simulationParameter} must be finite numeric")
            converted = float(raw) * entry.scale + entry.offset
            if not math.isfinite(converted):
                raise ValueError(f"converted model feature {entry.modelFeature} is not finite")
            values[entry.modelFeature] = converted
            audit.append(FeatureBindingAudit(**entry.model_dump(), sourceValue=float(raw), modelValue=converted))
        return BoundModelInput(experimentId=experiment_id, modelVersion=model_version,
                               bindingVersion=binding.bindingVersion,
                               suggestionRunId=binding.suggestionRunId, adapterPack=binding.adapterPack,
                               modelInputs=values, audit=audit)
