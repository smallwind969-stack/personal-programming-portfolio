from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

import httpx
import pytest

from app.result_interpretation.contracts import (
    InterpretationProviderOutput,
    MetricInterpretationDraft,
    NextExperimentDraft,
    ResultInterpretationProviderFailure,
    RiskExplanationDraft,
)
from app.result_interpretation.local_llm_provider import LocalLlmResultInterpretationProvider
from app.result_interpretation.policy import ResultInterpretationPolicy
from app.schemas.experiments import ExperimentTrainingResultMetrics, ExperimentTrainingResultSummary
from app.services.experiment_file_service import ExperimentFileService
from app.services.result_interpretation_agent import ResultInterpretationAgent


def service_with_result(experiment_id: str = "exp-result") -> ExperimentFileService:
    service = ExperimentFileService()
    service._training_results_by_experiment[experiment_id] = ExperimentTrainingResultSummary(
        experimentId=experiment_id, taskId="train-1", targetField="od600", status="completed",
        confidenceLevel="medium", metrics=ExperimentTrainingResultMetrics(mae=.18, rmse=.24, r2=.78),
        riskNotes=["样本批次仍然有限"], recommendations=["补充独立验证批次"],
        manualReviewItems=["复核异常点"], generatedAt="2026-07-20T00:00:00+00:00",
    )
    return service


def valid_output() -> InterpretationProviderOutput:
    return InterpretationProviderOutput(
        overallSummary="当前模型具备初步解释价值，但仍需增加独立批次验证。",
        metricInterpretations=[
            MetricInterpretationDraft(metricKey="mae", interpretation="平均绝对误差需结合业务容忍范围复核。", evidenceRefs=["metric:mae"]),
            MetricInterpretationDraft(metricKey="rmse", interpretation="均方根误差反映较大偏差的影响。", evidenceRefs=["metric:rmse"]),
            MetricInterpretationDraft(metricKey="r2", interpretation="解释度达到演示准入参考范围。", evidenceRefs=["metric:r2"]),
        ],
        observedPatterns=[], riskExplanations=[RiskExplanationDraft(riskId="risk:0", explanation="样本批次有限会降低跨批次可信度。", evidenceRefs=["risk:0"])],
        nextExperimentSuggestions=[NextExperimentDraft(title="增加独立批次", purpose="检验跨批次稳定性", evidenceRefs=["risk:0"], validationItems=["独立批次 R² 与误差变化"])],
        unresolvedQuestions=["异常点是否来自真实工艺波动"],
    )


class FakeProvider:
    provider = "fake-local"
    model = "qwen-test"
    def __init__(self, output=None, failure=None): self.output, self.failure, self.calls = output or valid_output(), failure, 0
    def interpret(self, context):
        self.calls += 1
        if self.failure: raise self.failure
        return self.output


def test_context_contains_authoritative_metrics_but_no_raw_rows_or_secrets() -> None:
    agent = ResultInterpretationAgent(service_with_result(), FakeProvider())
    context = agent.build_context("exp-result")
    assert context.metrics == {"mae": .18, "rmse": .24, "r2": .78}
    text = context.model_dump_json()
    assert "rawRows" not in text and "apiKey" not in text and "contentHash" not in text


def test_policy_rejects_unknown_metric_and_evidence() -> None:
    agent = ResultInterpretationAgent(service_with_result(), FakeProvider())
    context = agent.build_context("exp-result")
    invalid = valid_output().model_copy(update={"metricInterpretations": [MetricInterpretationDraft(metricKey="auc", interpretation="未知指标", evidenceRefs=["metric:auc"])]})
    with pytest.raises(ResultInterpretationProviderFailure) as error:
        ResultInterpretationPolicy().validate(context, invalid)
    assert error.value.category == "policyRejected"


def test_policy_rejects_selective_omission_of_metric_or_risk() -> None:
    agent = ResultInterpretationAgent(service_with_result(), FakeProvider())
    context = agent.build_context("exp-result")
    missing_risk = valid_output().model_copy(update={"riskExplanations": []})
    with pytest.raises(ResultInterpretationProviderFailure):
        ResultInterpretationPolicy().validate(context, missing_risk)
    missing_metrics = valid_output().model_copy(update={"metricInterpretations": []})
    with pytest.raises(ResultInterpretationProviderFailure):
        ResultInterpretationPolicy().validate(context, missing_metrics)


def test_policy_rejects_production_control_or_admission_claims() -> None:
    context = ResultInterpretationAgent(service_with_result(), FakeProvider()).build_context("exp-result")
    dangerous = valid_output().model_copy(update={"overallSummary": "批准仿真并下发指令控制产线"})
    with pytest.raises(ResultInterpretationProviderFailure):
        ResultInterpretationPolicy().validate(context, dangerous)


def test_agent_preserves_authoritative_metrics_and_falls_back_safely() -> None:
    service = service_with_result()
    before = service.get_latest_training_result("exp-result").model_copy(deep=True)
    agent = ResultInterpretationAgent(service, FakeProvider(failure=ResultInterpretationProviderFailure("timeout")))
    run = agent.create_run("exp-result", "cmd-1")
    assert run.mode == "rule_fallback" and run.fallbackReason == "timeout"
    assert run.authoritativeMetrics.r2 == .78
    assert service.get_latest_training_result("exp-result") == before


def test_agent_is_idempotent_and_parallel_across_experiments() -> None:
    service = service_with_result()
    service._training_results_by_experiment["exp-result-2"] = service.get_latest_training_result("exp-result").model_copy(update={"experimentId": "exp-result-2"})
    barrier = Barrier(2, timeout=1)
    class ParallelProvider(FakeProvider):
        def interpret(self, context): self.calls += 1; barrier.wait(); return self.output
    provider = ParallelProvider()
    agent = ResultInterpretationAgent(service, provider)
    with ThreadPoolExecutor(max_workers=2) as pool:
        runs = [pool.submit(agent.create_run, exp, f"cmd-{exp}") for exp in ("exp-result", "exp-result-2")]
        assert all(item.result().status == "completed" for item in runs)
    assert provider.calls == 2
    assert agent.create_run("exp-result", "cmd-exp-result").runId == runs[0].result().runId


def test_local_provider_rejects_extra_metric_value_field() -> None:
    content = '{"overallSummary":"解释","metricInterpretations":[{"metricKey":"r2","metricValue":0.99,"interpretation":"文本","evidenceRefs":["metric:r2"]}],"observedPatterns":[],"riskExplanations":[],"nextExperimentSuggestions":[],"unresolvedQuestions":[]}'
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"message": {"content": content}})))
    provider = LocalLlmResultInterpretationProvider(provider="ollama", model="qwen", base_url="http://local", api_key="", enabled=True, client=client)
    context = ResultInterpretationAgent(service_with_result(), FakeProvider()).build_context("exp-result")
    with pytest.raises(ResultInterpretationProviderFailure) as error:
        provider.interpret(context)
    assert error.value.category == "invalidResponse"


def test_result_interpretation_api_create_get_and_404(monkeypatch) -> None:
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.result_interpretation_agent import result_interpretation_agent
    result_interpretation_agent.file_service._training_results_by_experiment["exp-result-api"] = service_with_result().get_latest_training_result("exp-result").model_copy(update={"experimentId": "exp-result-api"})
    result_interpretation_agent._runs.clear(); result_interpretation_agent._commands.clear()
    monkeypatch.setattr(result_interpretation_agent, "provider", FakeProvider())
    client = TestClient(app)
    created = client.post("/experiments/exp-result-api/result-interpretation-runs", json={"commandId": "api-1"})
    assert created.status_code == 200
    body = created.json()
    assert body["authoritativeMetrics"]["r2"] == .78
    assert client.get(f"/experiments/exp-result-api/result-interpretation-runs/{body['runId']}").json() == body
    assert client.get("/experiments/exp-result-api/result-interpretation-runs/missing").status_code == 404


def test_model_evaluation_node_executes_result_interpretation_agent(monkeypatch) -> None:
    from app.agent_runtime.deterministic import DeterministicRuntimeAdapter
    from app.services.agent_orchestrator import AgentOrchestrator
    from app.services.result_interpretation_agent import result_interpretation_agent
    result_interpretation_agent.file_service._training_results_by_experiment["exp-result-node"] = service_with_result().get_latest_training_result("exp-result").model_copy(update={"experimentId": "exp-result-node"})
    result_interpretation_agent._runs.clear(); result_interpretation_agent._commands.clear()
    monkeypatch.setattr(result_interpretation_agent, "provider", FakeProvider())
    orchestrator = AgentOrchestrator(runtime=DeterministicRuntimeAdapter(), runtime_backend="deterministic")
    run = orchestrator.create_run("exp-result-node")
    for index in range(5):
        run = orchestrator.advance("exp-result-node", run.runId, run.runtimeRevision, f"advance-{index}")
    assert run.currentNodeId == "model-evaluation"
    run = orchestrator.advance("exp-result-node", run.runId, run.runtimeRevision, "advance-evaluation")
    state = orchestrator._runtime.get(run.runtimeRunId).state
    assert state["resultInterpretation"]["runId"].startswith("interpretation-run-")
    assert state["resultInterpretation"]["mode"] == "llm_assisted"
