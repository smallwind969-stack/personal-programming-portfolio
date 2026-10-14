from __future__ import annotations

from concurrent.futures import Future
from datetime import datetime, timezone
import os
from threading import RLock
from uuid import uuid4

from app.result_interpretation.contracts import ResultInterpretationContext, ResultInterpretationProvider, ResultInterpretationProviderFailure, ResultRiskContext
from app.result_interpretation.local_llm_provider import LocalLlmResultInterpretationProvider
from app.result_interpretation.policy import ResultInterpretationPolicy
from app.schemas.experiments import ResultInterpretationRun, ResultMetricInterpretation, ResultNextExperimentSuggestion, ResultObservedPattern, ResultRiskExplanation
from app.services.experiment_file_service import ExperimentFileService, experiment_file_service
from app.services.llm_service import local_llm_service


class ResultInterpretationAgent:
    def __init__(self, file_service: ExperimentFileService, provider: ResultInterpretationProvider) -> None:
        self.file_service, self.provider, self.policy = file_service, provider, ResultInterpretationPolicy()
        self._runs: dict[str, ResultInterpretationRun] = {}
        self._commands: dict[tuple[str, str], str] = {}
        self._inflight: dict[tuple[str, str], Future[ResultInterpretationRun]] = {}
        self._lock = RLock()

    def build_context(self, experiment_id: str) -> ResultInterpretationContext:
        result = self.file_service.get_latest_training_result(experiment_id)
        return ResultInterpretationContext(
            experimentId=experiment_id, taskId=result.taskId, targetField=result.targetField,
            status=result.status, confidenceLevel=result.confidenceLevel,
            metrics=result.metrics.model_dump(),
            risks=[ResultRiskContext(riskId=f"risk:{index}", text=text) for index, text in enumerate(result.riskNotes)],
            existingRecommendations=list(result.recommendations), manualReviewItems=list(result.manualReviewItems),
            generatedAt=result.generatedAt,
        )

    def create_run(self, experiment_id: str, command_id: str) -> ResultInterpretationRun:
        key = (experiment_id, command_id)
        with self._lock:
            prior = self._commands.get(key)
            if prior: return self._runs[prior].model_copy(deep=True)
            future = self._inflight.get(key); owner = future is None
            if owner: future = Future(); self._inflight[key] = future
        if not owner: return future.result().model_copy(deep=True)
        try: run = self._execute(experiment_id, command_id)
        except BaseException as exc:
            with self._lock: self._inflight.pop(key, None); future.set_exception(exc)
            raise
        with self._lock:
            self._runs[run.runId], self._commands[key] = run, run.runId
            self._inflight.pop(key, None); future.set_result(run.model_copy(deep=True))
            return run.model_copy(deep=True)

    def _execute(self, experiment_id: str, command_id: str) -> ResultInterpretationRun:
        context = self.build_context(experiment_id)
        fallback = None
        try:
            output = self.policy.validate(context, self.provider.interpret(context)); mode = "llm_assisted"
        except ResultInterpretationProviderFailure as exc:
            fallback, output, mode = exc.category, self.policy.fallback(context), "rule_fallback"
        risks = {item.riskId: item.text for item in context.risks}
        return ResultInterpretationRun(
            runId=f"interpretation-run-{uuid4().hex[:12]}", experimentId=experiment_id, commandId=command_id,
            status="completed", mode=mode, provider=self.provider.provider, model=self.provider.model,
            sourceTaskId=context.taskId, sourceGeneratedAt=context.generatedAt,
            authoritativeMetrics=context.metrics, confidenceLevel=context.confidenceLevel,
            overallSummary=output.overallSummary,
            metricInterpretations=[ResultMetricInterpretation(metricKey=item.metricKey, value=context.metrics[item.metricKey], interpretation=item.interpretation, evidenceRefs=item.evidenceRefs) for item in output.metricInterpretations],
            observedPatterns=[ResultObservedPattern(**item.model_dump()) for item in output.observedPatterns],
            riskExplanations=[ResultRiskExplanation(riskId=item.riskId, originalRisk=risks[item.riskId], explanation=item.explanation, evidenceRefs=item.evidenceRefs) for item in output.riskExplanations],
            nextExperimentSuggestions=[ResultNextExperimentSuggestion(**item.model_dump()) for item in output.nextExperimentSuggestions],
            unresolvedQuestions=output.unresolvedQuestions, fallbackReason=fallback, rejectedCount=1 if fallback == "policyRejected" else 0,
            createdAt=datetime.now(timezone.utc).isoformat(),
        )

    def get_run(self, experiment_id: str, run_id: str) -> ResultInterpretationRun | None:
        run = self._runs.get(run_id)
        return run.model_copy(deep=True) if run and run.experimentId == experiment_id else None


result_interpretation_agent = ResultInterpretationAgent(experiment_file_service, LocalLlmResultInterpretationProvider(
    provider=local_llm_service.provider, model=local_llm_service.model, base_url=local_llm_service.base_url,
    api_key=local_llm_service.api_key,
    enabled=local_llm_service.enabled and os.getenv("RESULT_INTERPRETATION_LLM_ENABLED", "false").lower() == "true",
    timeout=local_llm_service.timeout,
))
