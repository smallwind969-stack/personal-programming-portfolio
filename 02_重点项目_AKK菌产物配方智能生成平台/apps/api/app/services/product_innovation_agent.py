from __future__ import annotations

from concurrent.futures import Future
from datetime import datetime, timezone
import os
from threading import RLock
from uuid import uuid4

from app.product_innovation.contracts import InnovationEvidence, InnovationProviderFailure, ProductInnovationInput, ProductInnovationProvider, ProductInnovationRun
from app.product_innovation.local_llm_provider import LocalLlmProductInnovationProvider
from app.product_innovation.policy import FIXED_BOUNDARIES, ProductInnovationPolicy
from app.services.knowledge_service import KnowledgeService, knowledge_service
from app.services.llm_service import local_llm_service
from app.product_innovation.store import SqliteProductInnovationStore


class ProductInnovationAgent:
    def __init__(self, provider: ProductInnovationProvider, knowledge: KnowledgeService | None = None, run_store: SqliteProductInnovationStore | None = None) -> None:
        self.provider, self.knowledge, self.policy = provider, knowledge, ProductInnovationPolicy()
        self._store = run_store
        self._runs: dict[str, ProductInnovationRun] = {}
        self._commands: dict[tuple[str, str], str] = {}
        self._inflight: dict[tuple[str, str], Future[ProductInnovationRun]] = {}
        self._lock = RLock()
        if self._store:
            for run in self._store.load_runs():
                self._runs[run.runId] = run
                self._commands[(run.experimentId, run.commandId)] = run.runId

    def create_run(self, experiment_id: str, command_id: str, request: ProductInnovationInput) -> ProductInnovationRun:
        key = (experiment_id, command_id)
        with self._lock:
            prior = self._commands.get(key)
            if prior: return self._runs[prior].model_copy(deep=True)
            future = self._inflight.get(key); owner = future is None
            if owner: future = Future(); self._inflight[key] = future
        if not owner: return future.result().model_copy(deep=True)
        try: run = self._execute(experiment_id, command_id, request)
        except BaseException as exc:
            with self._lock: self._inflight.pop(key, None); future.set_exception(exc)
            raise
        with self._lock:
            self._runs[run.runId], self._commands[key] = run, run.runId
            if self._store: self._store.save_run(run)
            self._inflight.pop(key, None); future.set_result(run.model_copy(deep=True))
            return run.model_copy(deep=True)

    def _execute(self, experiment_id: str, command_id: str, request: ProductInnovationInput) -> ProductInnovationRun:
        evidence = []
        if self.knowledge:
            for item in self.knowledge.search_items(request.brief)[:5]:
                evidence.append(InnovationEvidence(evidenceId=f"knowledge:{item.knowledgeId}", title=item.title, evidenceLevel=item.evidenceLevel))
        context = self.policy.build_context(experiment_id, request, evidence)
        fallback = None
        try:
            output = self.policy.validate(context, self.provider.innovate(context)); mode = "llm_assisted"
        except InnovationProviderFailure as exc:
            fallback, output, mode = exc.category, self.policy.fallback(context), "rule_fallback"
        output = output.model_copy(update={"regulatoryConstraints": list(dict.fromkeys([*output.regulatoryConstraints, *FIXED_BOUNDARIES]))})
        return ProductInnovationRun(
            **output.model_dump(), runId=f"innovation-run-{uuid4().hex[:12]}", experimentId=experiment_id,
            commandId=command_id, status="completed", mode=mode, provider=self.provider.provider, model=self.provider.model,
            fallbackReason=fallback, requiresHumanReview=True, createdAt=datetime.now(timezone.utc).isoformat(),
        )

    def get_run(self, experiment_id: str, run_id: str) -> ProductInnovationRun | None:
        run = self._runs.get(run_id)
        return run.model_copy(deep=True) if run and run.experimentId == experiment_id else None

    def latest_run(self, experiment_id: str) -> ProductInnovationRun | None:
        with self._lock:
            runs = [item for item in self._runs.values() if item.experimentId == experiment_id]
            latest = max(runs, key=lambda item: item.createdAt) if runs else None
            return latest.model_copy(deep=True) if latest else None


_innovation_store_path = os.getenv("PRODUCT_INNOVATION_STORE_PATH", "").strip() or os.getenv("DOMAIN_RUN_STORE_PATH", "").strip()
_product_innovation_store = SqliteProductInnovationStore(_innovation_store_path) if _innovation_store_path else None

product_innovation_agent = ProductInnovationAgent(
    LocalLlmProductInnovationProvider(
        provider=local_llm_service.provider, model=local_llm_service.model, base_url=local_llm_service.base_url,
        api_key=local_llm_service.api_key,
        enabled=local_llm_service.enabled and os.getenv("PRODUCT_INNOVATION_LLM_ENABLED", "false").lower() == "true",
        timeout=local_llm_service.timeout,
    ),
    knowledge_service, run_store=_product_innovation_store,
)
