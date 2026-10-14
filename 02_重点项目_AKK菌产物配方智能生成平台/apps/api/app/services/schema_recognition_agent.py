from __future__ import annotations

from datetime import datetime, timezone
import os
from concurrent.futures import Future
from threading import RLock
from uuid import uuid4

from app.schema_recognition.contracts import SchemaProviderFailure, SchemaRecognitionProvider
from app.schema_recognition.policy import SchemaRecognitionPolicy
from app.schemas.experiments import SchemaRecognitionCandidate, SchemaRecognitionRun
from app.services.experiment_file_service import ExperimentFileService
from app.schema_recognition.local_llm_provider import LocalLlmSchemaRecognitionProvider
from app.services.experiment_file_service import experiment_file_service
from app.services.llm_service import local_llm_service


class SchemaRecognitionAgent:
    def __init__(self, file_service: ExperimentFileService, provider: SchemaRecognitionProvider) -> None:
        self.file_service, self.provider = file_service, provider
        self.policy = SchemaRecognitionPolicy()
        self._runs, self._commands = {}, {}
        self._inflight: dict[tuple[str, str], Future[SchemaRecognitionRun]] = {}
        self._lock = RLock()

    def create_run(self, experiment_id: str, command_id: str) -> SchemaRecognitionRun:
        with self._lock:
            prior = self._commands.get((experiment_id, command_id))
            if prior:
                return self._runs[prior].model_copy(deep=True)
            key = (experiment_id, command_id)
            future = self._inflight.get(key)
            owner = future is None
            if owner:
                future = Future()
                self._inflight[key] = future
        if not owner:
            return future.result().model_copy(deep=True)
        try:
            run = self._execute(experiment_id, command_id)
        except BaseException as exc:
            with self._lock:
                self._inflight.pop(key, None)
                future.set_exception(exc)
            raise
        with self._lock:
            self._runs[run.runId], self._commands[(experiment_id, command_id)] = run, run.runId
            self._inflight.pop(key, None)
            future.set_result(run.model_copy(deep=True))
            return run.model_copy(deep=True)

    def _execute(self, experiment_id: str, command_id: str) -> SchemaRecognitionRun:
        context = self.file_service.build_schema_recognition_context(experiment_id, sample_limit=3)
        rules = self._rule_candidates(experiment_id)
        fallback, rejected_count = None, 0
        try:
            validated, rejected = self.policy.validate_candidates(context, self.provider.recognize(context))
            rejected_count = len(rejected)
            candidates, conflicts = self.policy.merge(rules, validated)
            mode = "llm_assisted"
        except SchemaProviderFailure as exc:
            fallback, candidates, conflicts, mode = exc.category, rules, 0, "rule_fallback"
        return SchemaRecognitionRun(
            runId=f"schema-run-{uuid4().hex[:12]}", experimentId=experiment_id,
            commandId=command_id, status="completed", mode=mode,
            provider=self.provider.provider, model=self.provider.model,
            fallbackReason=fallback, candidateCount=len(candidates),
            reviewCount=sum(item.requiresHumanReview for item in candidates),
            conflictCount=conflicts, rejectedCount=rejected_count, candidates=candidates,
            createdAt=datetime.now(timezone.utc).isoformat(),
        )

    def get_run(self, experiment_id: str, run_id: str) -> SchemaRecognitionRun | None:
        run = self._runs.get(run_id)
        return run.model_copy(deep=True) if run and run.experimentId == experiment_id else None

    def _rule_candidates(self, experiment_id: str) -> list[SchemaRecognitionCandidate]:
        result = []
        for asset in self.file_service.suggest_field_mappings(experiment_id).assets:
            for item in asset.suggestions:
                if not item.standardField:
                    continue
                is_time = item.standardField == "timestamp"
                result.append(SchemaRecognitionCandidate(
                    assetId=asset.assetId, originalColumn=item.originalColumn,
                    standardField=item.standardField, dataType="datetime" if is_time else "number",
                    sourceUnit=item.unit, targetUnit=item.unit, isTimeField=is_time,
                    confidence=item.confidenceScore, evidence=[item.reason],
                    requiresHumanReview=item.requiresHumanConfirmation,
                    reviewReasons=["ruleLowConfidence"] if item.requiresHumanConfirmation else [], source="rule",
                ))
        return result


schema_recognition_agent = SchemaRecognitionAgent(
    experiment_file_service,
    LocalLlmSchemaRecognitionProvider(
        provider=local_llm_service.provider,
        model=local_llm_service.model,
        base_url=local_llm_service.base_url,
        api_key=local_llm_service.api_key,
        enabled=local_llm_service.enabled and os.getenv("SCHEMA_RECOGNITION_LLM_ENABLED", "false").lower() == "true",
        timeout=local_llm_service.timeout,
    ),
)
