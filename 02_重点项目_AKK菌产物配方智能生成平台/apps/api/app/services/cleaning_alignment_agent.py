from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from threading import RLock
from uuid import uuid4

from app.schemas.experiments import (
    CleaningAlignmentConfig,
    CleaningAlignmentQuality,
    CleaningAlignmentRun,
    CleaningFieldConversionEvidence,
)
from app.services.data_collection_localization_agent import (
    DataCollectionLocalizationAgent,
    data_collection_localization_agent,
)
from app.services.experiment_data_store import SqliteExperimentDataStore
from app.services.experiment_file_service import ExperimentFileService, experiment_file_service
from app.services.experiment_service import ExperimentService, experiment_service


def _hash(payload: object) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _normalize_timestamp(value: str) -> str | None:
    text = value.strip()
    if not text:
        return None
    # A number of industrial exporters emit .NET-style seven-digit fractional
    # seconds. Python datetime stores microseconds, so retain the first six
    # digits instead of incorrectly classifying the timestamp as invalid.
    text = re.sub(
        r"(\.\d{6})\d+(?=(?:[+-]\d{2}:\d{2})?$)",
        r"\1",
        text,
    )
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


class CleaningAlignmentAgent:
    def __init__(
        self,
        file_service: ExperimentFileService,
        workspace_service: ExperimentService,
        intake_agent: DataCollectionLocalizationAgent,
        store: SqliteExperimentDataStore | None = None,
    ) -> None:
        self.file_service = file_service
        self.workspace_service = workspace_service
        self.intake_agent = intake_agent
        self.store = store if store is not None else file_service.store
        self._runs: dict[str, list[CleaningAlignmentRun]] = {}
        self._lock = RLock()
        if self.store is not None:
            for payload in self.store.list("cleaning_alignment_run"):
                run = CleaningAlignmentRun.model_validate(payload)
                self._runs.setdefault(run.experimentId, []).append(run)

    def _input_payload(self, experiment_id: str) -> dict:
        assets = self.file_service.get_analysis_file_assets(experiment_id)
        source_evidence = self.file_service.get_source_evidence_stored_assets(experiment_id)
        mappings = self.file_service.get_confirmed_field_mappings(experiment_id)
        intake_runs = self.intake_agent.list_runs(experiment_id)
        return {
            "assets": [
                {"assetId": item.assetId, "contentHash": item.contentHash}
                for item in sorted(assets, key=lambda item: item.assetId)
            ],
            "sourceEvidence": [
                {"assetId": item.asset_id, "contentHash": item.content_hash}
                for item in sorted(source_evidence, key=lambda item: item.asset_id)
            ],
            "mappings": sorted(
                [item.model_dump(mode="json") for item in mappings.mappings],
                key=lambda item: (item["assetId"], item["originalColumn"]),
            ),
            "intakeRuns": sorted(
                [
                    {
                        "runId": run.runId, "status": run.status,
                        "transformations": [
                            item.model_dump(mode="json") for item in run.transformations
                        ],
                    }
                    for run in intake_runs
                ],
                key=lambda item: item["runId"],
            ),
        }

    def current_input_fingerprint(self, experiment_id: str) -> str:
        return _hash(self._input_payload(experiment_id))

    def create_run(
        self, experiment_id: str, config: CleaningAlignmentConfig,
    ) -> CleaningAlignmentRun:
        assets = self.file_service.get_analysis_stored_assets(experiment_id)
        mappings = self.file_service.get_confirmed_field_mappings(experiment_id)
        if not assets:
            raise ValueError("cleaning requires at least one parsed file asset")
        if mappings.mappingCount == 0:
            raise ValueError("cleaning requires human-confirmed field mappings")
        intake_runs = self.intake_agent.list_runs(experiment_id)
        if intake_runs and any(run.status != "confirmed" for run in intake_runs):
            raise ValueError("data intake human confirmation is required before cleaning")

        mapping_by_key = {
            (item.assetId, item.originalColumn): item for item in mappings.mappings
        }
        transform_by_key = {
            (item.assetId, item.originalColumn): item
            for run in intake_runs for item in run.transformations
        }
        quality = CleaningAlignmentQuality()
        rows_by_timestamp: dict[str, dict[str, str | float | None]] = {}
        evidence: list[CleaningFieldConversionEvidence] = []
        for asset in assets:
            mapped_columns = {
                column for (asset_id, column) in mapping_by_key if asset_id == asset.asset_id
            }
            quality.unmappedColumnCount += len(
                [column for column in asset.column_names if column not in mapped_columns]
            )
            for original_column in asset.column_names:
                mapping = mapping_by_key.get((asset.asset_id, original_column))
                if mapping is None:
                    continue
                transform = transform_by_key.get((asset.asset_id, original_column))
                scale = transform.scale if transform else 1.0
                offset = transform.offset if transform else 0.0
                before = next(
                    (row.get(original_column) for row in asset.rows if row.get(original_column)),
                    None,
                )
                after: str | float | None = None
                if before is not None:
                    if mapping.standardField == "timestamp":
                        after = _normalize_timestamp(before)
                    else:
                        try:
                            after = round(float(before) * scale + offset, config.numericPrecision)
                        except ValueError:
                            after = None
                evidence.append(CleaningFieldConversionEvidence(
                    assetId=asset.asset_id, originalColumn=original_column,
                    standardField=mapping.standardField,
                    sourceUnit=transform.sourceUnit if transform else mapping.unit,
                    targetUnit=transform.targetUnit if transform else mapping.unit,
                    scale=scale, offset=offset,
                    formula=f"target = source × {scale:g} + {offset:g}",
                    sampleBefore=before, sampleAfter=after,
                ))

            for row_index, raw_row in enumerate(asset.rows):
                cleaned: dict[str, str | float | None] = {}
                timestamp: str | None = None
                for original_column in asset.column_names:
                    mapping = mapping_by_key.get((asset.asset_id, original_column))
                    if mapping is None:
                        continue
                    raw = raw_row.get(original_column, "")
                    if raw == "":
                        quality.missingValueCount += 1
                        cleaned[mapping.standardField] = None
                        continue
                    if mapping.standardField == "timestamp":
                        timestamp = _normalize_timestamp(raw)
                        if timestamp is None:
                            quality.invalidTimestampCount += 1
                        cleaned["timestamp"] = timestamp
                        continue
                    transform = transform_by_key.get((asset.asset_id, original_column))
                    scale = transform.scale if transform else 1.0
                    offset = transform.offset if transform else 0.0
                    try:
                        cleaned[mapping.standardField] = round(
                            float(raw) * scale + offset, config.numericPrecision,
                        )
                    except ValueError:
                        quality.invalidNumericCount += 1
                        cleaned[mapping.standardField] = None
                alignment_key = timestamp or f"invalid:{asset.asset_id}:{row_index}"
                if alignment_key in rows_by_timestamp:
                    quality.duplicateTimestampCount += 1
                    rows_by_timestamp[alignment_key].update(cleaned)
                else:
                    rows_by_timestamp[alignment_key] = cleaned

        aligned_rows = [
            rows_by_timestamp[key] for key in sorted(rows_by_timestamp)
        ]
        quality_total = sum(quality.model_dump().values())
        now = datetime.now(timezone.utc).isoformat()
        run = CleaningAlignmentRun(
            runId=f"clean-align-{uuid4().hex[:12]}",
            experimentId=experiment_id,
            runVersion=len(self._runs.get(experiment_id, [])) + 1,
            status="needsReview" if quality_total else "completed",
            config=config,
            inputFingerprint=self.current_input_fingerprint(experiment_id),
            outputHash=_hash(aligned_rows),
            assetCount=len(assets), mappingCount=mappings.mappingCount,
            alignedRowCount=len(aligned_rows), alignedRows=aligned_rows,
            conversionEvidence=evidence, quality=quality, createdAt=now,
        )
        with self._lock:
            self._runs.setdefault(experiment_id, []).append(run)
            self._persist(run)
        return run.model_copy(deep=True)

    def _persist(self, run: CleaningAlignmentRun) -> None:
        if self.store is not None:
            self.store.save(
                "cleaning_alignment_run", run.runId, run.experimentId,
                run.model_dump(mode="json"),
            )

    def list_runs(self, experiment_id: str) -> list[CleaningAlignmentRun]:
        with self._lock:
            return [item.model_copy(deep=True) for item in self._runs.get(experiment_id, [])]

    def latest_run(self, experiment_id: str) -> CleaningAlignmentRun | None:
        runs = self.list_runs(experiment_id)
        return runs[-1] if runs else None

    def confirm_review(
        self, experiment_id: str, run_id: str, operator: str, reason: str,
    ) -> CleaningAlignmentRun:
        if not operator.strip() or len(reason.strip()) < 2:
            raise ValueError("quality review requires operator and reason")
        with self._lock:
            runs = self._runs.get(experiment_id, [])
            index = next((i for i, item in enumerate(runs) if item.runId == run_id), None)
            if index is None:
                raise LookupError("cleaning alignment run was not found")
            run = runs[index]
            if run.status != "needsReview":
                raise ValueError("only a run needing quality review can be confirmed")
            updated = run.model_copy(update={
                "status": "confirmed", "reviewedBy": operator.strip(),
                "reviewReason": reason.strip(),
                "reviewedAt": datetime.now(timezone.utc).isoformat(),
            })
            runs[index] = updated
            self._persist(updated)
            return updated.model_copy(deep=True)

    def assert_snapshot_ready(self, experiment_id: str) -> CleaningAlignmentRun:
        run = self.latest_run(experiment_id)
        if run is None:
            raise ValueError("a cleaning alignment run is required before dataset snapshot")
        if run.status not in {"completed", "confirmed"}:
            raise ValueError("cleaning alignment quality review is required before dataset snapshot")
        if run.inputFingerprint != self.current_input_fingerprint(experiment_id):
            raise ValueError("cleaning alignment input fingerprint is stale")
        return run


cleaning_alignment_agent = CleaningAlignmentAgent(
    experiment_file_service, experiment_service,
    data_collection_localization_agent, experiment_file_service.store,
)
