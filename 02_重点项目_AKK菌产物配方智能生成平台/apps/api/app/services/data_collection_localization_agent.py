from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from app.feature_binding_advisor.adapter_pack import DeviceAdapterPackService
from app.schemas.experiments import (
    DataCollectionLocalizationRun,
    DataIntakeFieldTransformation,
    ExperimentConfirmFieldMappingsRequest,
)
from app.services.experiment_file_service import ExperimentFileService, experiment_file_service
from app.services.experiment_data_store import SqliteExperimentDataStore
from app.services.experiment_service import ExperimentService, experiment_service
from app.services.feature_binding_advisor_agent import device_adapter_pack_service


_CANONICAL_FIELDS = {
    "timestamp": ("timestamp", None, None),
    "temperature_c": ("temperature_c", "temperatureC", "°C"),
    "ph": ("ph", "ph", "pH"),
    "agitation_rpm": ("agitation_rpm", "stirringRpm", "rpm"),
    "dissolved_oxygen_pct": ("dissolved_oxygen_pct", "dissolvedOxygenPct", "%"),
    "od600": ("od600", None, "AU"),
}


class DataCollectionLocalizationAgent:
    """Orchestrates file parsing tools, locked adapters, evidence, and human gates."""

    def __init__(
        self,
        file_service: ExperimentFileService,
        workspace_service: ExperimentService,
        adapter_service: DeviceAdapterPackService,
        store: SqliteExperimentDataStore | None = None,
    ) -> None:
        self.file_service = file_service
        self.workspace_service = workspace_service
        self.adapter_service = adapter_service
        self.store = store if store is not None else file_service.store
        self._runs: dict[str, list[DataCollectionLocalizationRun]] = {}
        self._lock = RLock()
        if self.store is not None:
            for payload in self.store.list("data_intake_run"):
                run = DataCollectionLocalizationRun.model_validate(payload)
                self._runs.setdefault(run.experimentId, []).append(run)

    def create_run(self, experiment_id: str, asset_id: str) -> DataCollectionLocalizationRun:
        with self._lock:
            existing = next(
                (run for run in self._runs.get(experiment_id, []) if run.assetId == asset_id),
                None,
            )
        if existing is not None:
            return existing.model_copy(deep=True)
        context = self.file_service.build_schema_recognition_context(experiment_id)
        asset = next((item for item in context.assets if item.assetId == asset_id), None)
        if asset is None:
            raise LookupError("uploaded experiment asset was not found")
        overview = self.workspace_service.get_workspace_overview(experiment_id)
        reference = overview.adapterPack if overview else None
        entries_by_alias = {}
        if reference is not None:
            pack = self.adapter_service.get_verified(
                reference.enterpriseKey, reference.deviceType, reference.packVersion,
            )
            if pack is None:
                raise LookupError("locked device adapter pack was not found")
            if pack.packId != reference.packId or pack.contentHash != reference.contentHash:
                raise ValueError("locked device adapter pack failed lineage verification")
            entries_by_alias = {entry.sourceFieldAlias.casefold(): entry for entry in pack.entries}

        transformations = []
        for field in asset.fields:
            entry = entries_by_alias.get(field.originalColumn.casefold())
            if entry is None:
                canonical = _CANONICAL_FIELDS.get(field.originalColumn.casefold())
                if canonical is not None:
                    standard_field, simulation_parameter, unit = canonical
                    transformations.append(DataIntakeFieldTransformation(
                        assetId=asset_id,
                        originalColumn=field.originalColumn,
                        matched=True,
                        standardField=standard_field,
                        simulationParameter=simulation_parameter,
                        sourceUnit=unit,
                        targetUnit=unit,
                        evidence=[
                            f"Canonical standard-field match: {field.originalColumn} -> {standard_field}.",
                            "No conversion is applied; target = source × 1 + 0.",
                        ],
                        requiresHumanReview=True,
                    ))
                    continue
                transformations.append(DataIntakeFieldTransformation(
                    assetId=asset_id, originalColumn=field.originalColumn, matched=False,
                    evidence=["No exact alias was found in the locked adapter pack; human mapping is required."],
                ))
            else:
                transformations.append(DataIntakeFieldTransformation(
                    assetId=asset_id, originalColumn=field.originalColumn, matched=True,
                    standardField=entry.standardField,
                    simulationParameter=entry.simulationParameter,
                    sourceUnit=entry.sourceUnit, targetUnit=entry.targetUnit,
                    scale=entry.scale, offset=entry.offset,
                    evidence=[
                        f"Exact adapter alias match: {entry.sourceFieldAlias}.",
                        f"Conversion formula: target = source × {entry.scale:g} + {entry.offset:g}.",
                    ],
                    requiresHumanReview=True,
                ))
        run = DataCollectionLocalizationRun(
            runId=f"intake-{uuid4().hex[:12]}",
            experimentId=experiment_id, assetId=asset_id, status="needsReview",
            managedWorkspace=overview is not None,
            adapterPack=reference,
            transformationCount=len(transformations),
            matchedCount=sum(item.matched for item in transformations),
            pendingReviewCount=len(transformations),
            transformations=transformations,
            createdAt=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._runs.setdefault(experiment_id, []).append(run)
            if self.store is not None:
                self.store.save(
                    "data_intake_run", run.runId, experiment_id,
                    run.model_dump(mode="json"),
                )
        return run.model_copy(deep=True)

    def list_runs(self, experiment_id: str) -> list[DataCollectionLocalizationRun]:
        with self._lock:
            return [run.model_copy(deep=True) for run in self._runs.get(experiment_id, [])]

    def discard_run(self, experiment_id: str, run_id: str) -> None:
        with self._lock:
            runs = self._runs.get(experiment_id, [])
            self._runs[experiment_id] = [run for run in runs if run.runId != run_id]
            if not self._runs[experiment_id]:
                self._runs.pop(experiment_id, None)
            if self.store is not None:
                self.store.soft_delete("data_intake_run", run_id)

    def latest_run(self, experiment_id: str) -> DataCollectionLocalizationRun | None:
        runs = self.list_runs(experiment_id)
        return runs[-1] if runs else None

    def confirm(
        self, experiment_id: str, request: ExperimentConfirmFieldMappingsRequest,
    ) -> DataCollectionLocalizationRun:
        runs = self._runs.get(experiment_id, [])
        if not runs:
            raise LookupError("data intake run was not found")
        supplied = {(item.assetId, item.originalColumn) for item in request.mappings if item.confirmed}
        required = {
            (item.assetId, item.originalColumn)
            for run in runs for item in run.transformations
            if run.managedWorkspace or run.adapterPack is not None or item.matched
        }
        missing = sorted(required - supplied)
        if missing:
            names = ", ".join(column for _, column in missing)
            raise ValueError(f"human confirmation is missing for adapter fields: {names}")
        self.file_service.confirm_field_mappings(experiment_id, request)
        mappings = {
            (item.assetId, item.originalColumn): item
            for item in request.mappings
        }
        with self._lock:
            confirmed_runs = []
            for run in runs:
                transformations = []
                for transformation in run.transformations:
                    confirmed_mapping = mappings.get(
                        (transformation.assetId, transformation.originalColumn)
                    )
                    if confirmed_mapping is None:
                        transformations.append(transformation)
                        continue
                    transformations.append(transformation.model_copy(update={
                        "standardField": confirmed_mapping.standardField,
                        "targetUnit": confirmed_mapping.unit,
                        "requiresHumanReview": False,
                        "evidence": [
                            *transformation.evidence,
                            f"Human confirmation by {confirmed_mapping.confirmedBy}.",
                        ],
                    }))
                updated = run.model_copy(update={
                    "status": "confirmed", "pendingReviewCount": 0,
                    "transformations": transformations,
                })
                confirmed_runs.append(updated)
                if self.store is not None:
                    self.store.save(
                        "data_intake_run", updated.runId, experiment_id,
                        updated.model_dump(mode="json"),
                    )
            self._runs[experiment_id] = confirmed_runs
            return confirmed_runs[-1].model_copy(deep=True)

    def assert_snapshot_ready(self, experiment_id: str) -> None:
        runs = self._runs.get(experiment_id, [])
        if runs and any(run.status != "confirmed" for run in runs):
            raise ValueError("data intake human confirmation is required before dataset snapshot")


data_collection_localization_agent = DataCollectionLocalizationAgent(
    experiment_file_service, experiment_service, device_adapter_pack_service,
)
