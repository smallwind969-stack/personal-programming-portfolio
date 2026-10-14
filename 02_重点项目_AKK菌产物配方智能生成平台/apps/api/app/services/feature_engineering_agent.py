from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from statistics import mean, pstdev
from threading import RLock
from typing import Protocol
from uuid import uuid4

from app.schemas.experiments import (
    EngineeredFeatureDefinition,
    ExperimentDatasetSnapshot,
    FeatureEngineeringConfig,
    FeatureEngineeringRun,
    FeatureLeakageIssue,
)
from app.services.experiment_data_store import SqliteExperimentDataStore
from app.services.experiment_file_service import experiment_file_service


def _hash(payload: object) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _numeric(value: object) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


class DatasetSnapshotSource(Protocol):
    def get_latest_dataset_snapshot(self, experiment_id: str) -> ExperimentDatasetSnapshot:
        ...


class FeatureEngineeringAgent:
    """Build immutable, auditable feature sets from a locked cleaning snapshot."""

    def __init__(
        self,
        snapshot_source: DatasetSnapshotSource,
        store: SqliteExperimentDataStore | None,
    ) -> None:
        self.snapshot_source = snapshot_source
        self.store = store
        self._runs: dict[str, list[FeatureEngineeringRun]] = {}
        self._lock = RLock()
        if store is not None:
            for payload in store.list("feature_engineering_run"):
                run = FeatureEngineeringRun.model_validate(payload)
                self._runs.setdefault(run.experimentId, []).append(run)
            for runs in self._runs.values():
                runs.sort(key=lambda item: item.runVersion)

    @staticmethod
    def _snapshot_identity(snapshot: ExperimentDatasetSnapshot) -> dict[str, str]:
        return {
            "snapshotId": snapshot.snapshotId,
            "contentHash": snapshot.contentHash,
            "cleaningRunId": snapshot.cleaningRunId or "",
            "cleaningOutputHash": snapshot.cleaningOutputHash or "",
        }

    def current_input_fingerprint(
        self, experiment_id: str, config: FeatureEngineeringConfig,
    ) -> str:
        snapshot = self.snapshot_source.get_latest_dataset_snapshot(experiment_id)
        return _hash({
            "snapshot": self._snapshot_identity(snapshot),
            "config": config.model_dump(mode="json"),
        })

    def create_run(
        self, experiment_id: str, config: FeatureEngineeringConfig,
    ) -> FeatureEngineeringRun:
        snapshot = self.snapshot_source.get_latest_dataset_snapshot(experiment_id)
        if snapshot.status != "modeling_ready" or not snapshot.snapshotId:
            raise ValueError("a modeling-ready dataset snapshot is required")
        if not snapshot.cleaningRunId or not snapshot.cleaningOutputHash:
            raise ValueError("feature engineering requires cleaning alignment lineage")
        if not snapshot.alignedRows:
            raise ValueError("feature engineering requires aligned snapshot rows")

        available_numeric = {
            key for row in snapshot.alignedRows for key, value in row.items()
            if key != "timestamp" and _numeric(value) is not None
        }
        if config.targetField not in available_numeric:
            raise ValueError("target field must exist as a numeric snapshot field")
        missing_sources = [
            field for field in config.sourceFields if field not in available_numeric
        ]
        if missing_sources:
            raise ValueError(
                "source feature fields are missing or non-numeric: "
                + ", ".join(missing_sources)
            )
        if config.targetField in config.sourceFields:
            raise ValueError("target field cannot also be a source feature")

        original_timestamps = [str(row.get("timestamp") or "") for row in snapshot.alignedRows]
        ordered_rows = sorted(
            [dict(row) for row in snapshot.alignedRows],
            key=lambda row: str(row.get("timestamp") or ""),
        )
        issues: list[FeatureLeakageIssue] = []
        if original_timestamps != [str(row.get("timestamp") or "") for row in ordered_rows]:
            issues.append(FeatureLeakageIssue(
                code="timestamp_order_corrected", severity="warning",
                message="输入行时间顺序不一致，特征工程已按时间升序重排。",
            ))

        feature_rows: list[dict[str, str | float | None]] = [
            {
                "timestamp": row.get("timestamp"),
                config.targetField: _numeric(row.get(config.targetField)),
            }
            for row in ordered_rows
        ]
        definitions_seed: list[
            tuple[str, str, str, str, int | None, int | None]
        ] = []

        for source_field in config.sourceFields:
            values = [_numeric(row.get(source_field)) for row in ordered_rows]
            finite_values = [value for value in values if value is not None]
            if finite_values and min(finite_values) == max(finite_values):
                issues.append(FeatureLeakageIssue(
                    code="constant_feature", severity="warning",
                    featureName=source_field,
                    message=f"{source_field} 在当前快照中为常量，建模贡献可能有限。",
                ))

            if config.includeRaw:
                definitions_seed.append((
                    source_field, "raw", source_field,
                    f"{source_field}[t]", None, None,
                ))
                for index, value in enumerate(values):
                    feature_rows[index][source_field] = value

            for lag in sorted(config.lagSteps):
                name = f"{source_field}_lag_{lag}"
                definitions_seed.append((
                    name, "lag", source_field,
                    f"{source_field}[t-{lag}]", lag, None,
                ))
                for index in range(len(values)):
                    feature_rows[index][name] = (
                        values[index - lag] if index >= lag else None
                    )

            if config.includeDiff:
                name = f"{source_field}_diff_1"
                definitions_seed.append((
                    name, "diff", source_field,
                    f"{source_field}[t] - {source_field}[t-1]", 1, None,
                ))
                for index, value in enumerate(values):
                    previous = values[index - 1] if index >= 1 else None
                    feature_rows[index][name] = (
                        value - previous
                        if value is not None and previous is not None else None
                    )

            for window in sorted(config.rollingWindows):
                mean_name = f"{source_field}_rolling_mean_{window}"
                std_name = f"{source_field}_rolling_std_{window}"
                definitions_seed.extend([
                    (
                        mean_name, "rolling_mean", source_field,
                        f"mean({source_field}[t-{window - 1}:t])", None, window,
                    ),
                    (
                        std_name, "rolling_std", source_field,
                        f"std({source_field}[t-{window - 1}:t])", None, window,
                    ),
                ])
                for index in range(len(values)):
                    start = index - window + 1
                    window_values = values[start:index + 1] if start >= 0 else []
                    valid_window = (
                        len(window_values) == window
                        and all(value is not None for value in window_values)
                    )
                    numeric_window = [
                        float(value) for value in window_values if value is not None
                    ]
                    feature_rows[index][mean_name] = (
                        mean(numeric_window) if valid_window else None
                    )
                    feature_rows[index][std_name] = (
                        pstdev(numeric_window) if valid_window else None
                    )

        definitions: list[EngineeredFeatureDefinition] = []
        for name, kind, source, formula, lag, window in definitions_seed:
            valid_count = sum(
                _numeric(row.get(name)) is not None for row in feature_rows
            )
            if valid_count == 0:
                issues.append(FeatureLeakageIssue(
                    code="all_missing_feature", severity="blocking",
                    featureName=name,
                    message=f"{name} 没有任何可用于建模的有效值。",
                ))
            definitions.append(EngineeredFeatureDefinition(
                name=name, kind=kind, sourceField=source, formula=formula,
                lag=lag, window=window, validCount=valid_count,
                missingRate=round(1 - valid_count / len(feature_rows), 8),
            ))

        candidate_names = [definition.name for definition in definitions]
        usable_count = sum(
            _numeric(row.get(config.targetField)) is not None
            and all(_numeric(row.get(name)) is not None for name in candidate_names)
            for row in feature_rows
        )
        output_payload = {
            "targetField": config.targetField,
            "definitions": [item.model_dump(mode="json") for item in definitions],
            "featureRows": feature_rows,
            "leakageIssues": [item.model_dump(mode="json") for item in issues],
        }
        run = FeatureEngineeringRun(
            featureSetId=f"feature-set-{uuid4().hex[:12]}",
            experimentId=experiment_id,
            runVersion=len(self._runs.get(experiment_id, [])) + 1,
            status="needsReview", config=config,
            snapshotId=snapshot.snapshotId,
            snapshotContentHash=snapshot.contentHash,
            cleaningRunId=snapshot.cleaningRunId,
            cleaningOutputHash=snapshot.cleaningOutputHash,
            inputFingerprint=self.current_input_fingerprint(experiment_id, config),
            outputHash=_hash(output_payload), targetField=config.targetField,
            candidateFeatureNames=candidate_names, definitions=definitions,
            featureRows=feature_rows, rowCount=len(feature_rows),
            usableRowCount=usable_count, leakageIssues=issues,
            createdAt=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._runs.setdefault(experiment_id, []).append(run)
            self._persist(run)
        return run.model_copy(deep=True)

    def _persist(self, run: FeatureEngineeringRun) -> None:
        if self.store is not None:
            self.store.save(
                "feature_engineering_run", run.featureSetId, run.experimentId,
                run.model_dump(mode="json"),
            )

    def list_runs(self, experiment_id: str) -> list[FeatureEngineeringRun]:
        # Workers and API processes have independent Python memory. Reload the
        # authoritative SQLite records before every read so a confirmation made
        # in the web process is visible to a queued training task.
        self._refresh_from_store(experiment_id)
        with self._lock:
            return [
                item.model_copy(deep=True)
                for item in self._runs.get(experiment_id, [])
            ]

    def _refresh_from_store(self, experiment_id: str) -> None:
        if self.store is None:
            return
        persisted = [
            FeatureEngineeringRun.model_validate(payload)
            for payload in self.store.list("feature_engineering_run", experiment_id)
        ]
        persisted.sort(key=lambda item: item.runVersion)
        with self._lock:
            if persisted:
                self._runs[experiment_id] = persisted

    def latest_run(self, experiment_id: str) -> FeatureEngineeringRun | None:
        runs = self.list_runs(experiment_id)
        return runs[-1] if runs else None

    def confirm(
        self, experiment_id: str, feature_set_id: str, operator: str,
        reason: str, selected_feature_names: list[str],
    ) -> FeatureEngineeringRun:
        if not operator.strip() or len(reason.strip()) < 2:
            raise ValueError("feature set confirmation requires operator and reason")
        if (
            not selected_feature_names
            or len(selected_feature_names) != len(set(selected_feature_names))
        ):
            raise ValueError("selected feature names must be non-empty and unique")
        with self._lock:
            runs = self._runs.get(experiment_id, [])
            index = next(
                (position for position, item in enumerate(runs)
                 if item.featureSetId == feature_set_id),
                None,
            )
            if index is None:
                raise LookupError("feature engineering run was not found")
            run = runs[index]
            if run.status != "needsReview":
                raise ValueError("only a feature set needing review can be confirmed")
            unknown = [
                name for name in selected_feature_names
                if name not in run.candidateFeatureNames
            ]
            if unknown:
                raise ValueError(
                    "selected features must come from the candidate feature set"
                )
            blocked = {
                issue.featureName for issue in run.leakageIssues
                if issue.severity == "blocking" and issue.featureName
            }
            if blocked.intersection(selected_feature_names):
                raise ValueError(
                    "blocking leakage issues must be removed before confirmation"
                )
            if run.inputFingerprint != self.current_input_fingerprint(
                experiment_id, run.config,
            ):
                raise ValueError("feature engineering input fingerprint is stale")

            for position, prior in enumerate(runs):
                if prior.status == "confirmed":
                    superseded = prior.model_copy(update={"status": "superseded"})
                    runs[position] = superseded
                    self._persist(superseded)

            usable_count = sum(
                _numeric(row.get(run.targetField)) is not None
                and all(
                    _numeric(row.get(name)) is not None
                    for name in selected_feature_names
                )
                for row in run.featureRows
            )
            updated = run.model_copy(update={
                "status": "confirmed",
                "selectedFeatureNames": list(selected_feature_names),
                "usableRowCount": usable_count,
                "confirmedBy": operator.strip(),
                "confirmationReason": reason.strip(),
                "confirmedAt": datetime.now(timezone.utc).isoformat(),
            })
            runs[index] = updated
            self._persist(updated)
            return updated.model_copy(deep=True)

    def assert_training_ready(self, experiment_id: str) -> FeatureEngineeringRun:
        confirmed = [
            run for run in self.list_runs(experiment_id)
            if run.status == "confirmed"
        ]
        if not confirmed:
            raise ValueError(
                "feature engineering human confirmation is required before training"
            )
        run = confirmed[-1]
        if run.inputFingerprint != self.current_input_fingerprint(
            experiment_id, run.config,
        ):
            raise ValueError("confirmed feature engineering input fingerprint is stale")
        if not run.selectedFeatureNames:
            raise ValueError("confirmed feature set has no selected features")
        return run

    def export_numeric_training_dataset(self, experiment_id: str, snapshot_id: str):
        import numpy as np
        from app.research.sklearn_runner import NumericTrainingDataset

        run = self.assert_training_ready(experiment_id)
        if run.snapshotId != snapshot_id:
            raise ValueError(
                "confirmed feature set does not belong to requested snapshot"
            )
        complete_rows = [
            row for row in run.featureRows
            if _numeric(row.get(run.targetField)) is not None
            and all(
                _numeric(row.get(name)) is not None
                for name in run.selectedFeatureNames
            )
        ]
        if not complete_rows:
            raise ValueError("confirmed feature set has no complete training rows")
        return NumericTrainingDataset(
            experimentId=experiment_id, snapshotId=snapshot_id,
            datasetFingerprint=f"{run.inputFingerprint}:{run.outputHash}",
            featureNames=run.selectedFeatureNames, targetField=run.targetField,
            X=np.asarray([
                [float(row[name]) for name in run.selectedFeatureNames]
                for row in complete_rows
            ], dtype=float),
            y=np.asarray([
                float(row[run.targetField]) for row in complete_rows
            ], dtype=float),
        )


feature_engineering_agent = FeatureEngineeringAgent(
    experiment_file_service,
    experiment_file_service.store,
)
