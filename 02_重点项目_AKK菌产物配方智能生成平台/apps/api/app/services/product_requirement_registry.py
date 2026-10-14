from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from threading import RLock
from uuid import uuid4

from app.product_innovation.contracts import (
    ProductRequirementConfirmRequest,
    ProductRequirementSnapshot,
    ProductRequirementVersion,
)
from app.services.product_innovation_agent import ProductInnovationAgent, product_innovation_agent
from app.services.product_innovation_agent import _product_innovation_store
from app.product_innovation.store import SqliteProductInnovationStore


class ProductRequirementConflictError(RuntimeError):
    pass


class ProductRequirementNotFoundError(LookupError):
    pass


class ProductRequirementRegistry:
    """In-memory v1 registry; every returned object is a defensive deep copy."""

    def __init__(self, innovation_agent: ProductInnovationAgent, store: SqliteProductInnovationStore | None = None) -> None:
        self._innovation_agent = innovation_agent
        self._store = store
        self._versions: dict[str, ProductRequirementVersion] = {}
        self._ids_by_experiment: dict[str, list[str]] = {}
        self._version_by_source_run: dict[str, str] = {}
        self._confirmation_commands: dict[tuple[str, str], str] = {}
        self._lock = RLock()
        if self._store:
            for version in self._store.load_requirements():
                self._versions[version.requirementVersionId] = version
                self._ids_by_experiment.setdefault(version.experimentId, []).append(version.requirementVersionId)
                self._version_by_source_run[version.sourceRunId] = version.requirementVersionId
                self._confirmation_commands[(version.experimentId, version.confirmationCommandId)] = version.requirementVersionId

    def reset(self) -> None:
        with self._lock:
            self._versions.clear()
            self._ids_by_experiment.clear()
            self._version_by_source_run.clear()
            self._confirmation_commands.clear()
            if self._store: self._store.reset()

    def confirm(self, experiment_id: str, run_id: str, request: ProductRequirementConfirmRequest) -> ProductRequirementVersion:
        run = self._innovation_agent.get_run(experiment_id, run_id)
        if run is None:
            raise ProductRequirementNotFoundError(run_id)
        key = (experiment_id, request.commandId)
        with self._lock:
            prior_id = self._confirmation_commands.get(key)
            if prior_id:
                prior = self._versions[prior_id]
                if prior.sourceRunId != run_id:
                    raise ProductRequirementConflictError("Confirmation command already belongs to another innovation run")
                return prior.model_copy(deep=True)
            if run_id in self._version_by_source_run:
                raise ProductRequirementConflictError("Innovation run has already been confirmed")
            ids = self._ids_by_experiment.setdefault(experiment_id, [])
            parent_id = ids[-1] if ids else None
            snapshot = ProductRequirementSnapshot(
                **run.model_dump(include=set(ProductRequirementSnapshot.model_fields) - {"fixedBoundaries"}),
                fixedBoundaries=list(run.regulatoryConstraints),
            )
            canonical = json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            version = ProductRequirementVersion(
                requirementVersionId=f"product-requirement-{uuid4().hex[:12]}",
                experimentId=experiment_id,
                version=len(ids) + 1,
                parentVersionId=parent_id,
                sourceRunId=run.runId,
                sourceCommandId=run.commandId,
                confirmationCommandId=request.commandId,
                snapshot=snapshot,
                contentHash=f"sha256:{sha256(canonical.encode('utf-8')).hexdigest()}",
                operator=request.operator,
                reason=request.reason,
                confirmedAt=datetime.now(timezone.utc).isoformat(),
            )
            self._versions[version.requirementVersionId] = version
            ids.append(version.requirementVersionId)
            self._version_by_source_run[run_id] = version.requirementVersionId
            self._confirmation_commands[key] = version.requirementVersionId
            if self._store: self._store.save_requirement(version)
            return version.model_copy(deep=True)

    def list_versions(self, experiment_id: str) -> list[ProductRequirementVersion]:
        with self._lock:
            return [self._versions[item].model_copy(deep=True) for item in self._ids_by_experiment.get(experiment_id, [])]

    def latest(self, experiment_id: str) -> ProductRequirementVersion | None:
        with self._lock:
            ids = self._ids_by_experiment.get(experiment_id, [])
            return self._versions[ids[-1]].model_copy(deep=True) if ids else None


product_requirement_registry = ProductRequirementRegistry(product_innovation_agent, _product_innovation_store)
