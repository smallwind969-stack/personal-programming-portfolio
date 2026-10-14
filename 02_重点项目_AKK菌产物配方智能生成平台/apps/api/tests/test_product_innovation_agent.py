from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import json
import httpx

import pytest

from app.product_innovation.contracts import (
    InnovationMaterialRoleDraft,
    InnovationMetricDraft,
    InnovationProviderOutput,
    InnovationProviderFailure,
    InnovationSuggestionDraft,
    ProductInnovationInput,
)
from app.product_innovation.policy import ProductInnovationPolicy
from app.product_innovation.local_llm_provider import LocalLlmProductInnovationProvider
from app.services.product_innovation_agent import ProductInnovationAgent


def valid_output() -> InnovationProviderOutput:
    return InnovationProviderOutput(
        workingName="低糖发酵饮品概念",
        category="功能食品",
        problemStatement="探索低糖且具有稳定口感的发酵饮品研发方向。",
        targetUserTags=["关注糖摄入的成年人"], usageScenarios=["日常饮用"],
        valuePropositions=["低糖方向", "稳定口感"],
        targetMetrics=[InnovationMetricDraft(metricName="总糖", direction="decrease", unit="g/100mL", targetDescription="相对基线降低并通过检测确认", evidenceRefs=["input:brief"])],
        materialRoles=[InnovationMaterialRoleDraft(role="发酵底物", purpose="支持目标发酵过程", constraints=["食品级", "批次可追溯"], evidenceRefs=["input:brief"])],
        costAssumptions=["原料成本需要供应商报价后确认"],
        processConstraints=["参数必须通过小试确定"], regulatoryConstraints=["上市前完成适用法规审查"],
        risks=["低糖调整可能影响风味与稳定性"], unresolvedQuestions=["目标市场的糖含量标示门槛"],
        validationPlan=[InnovationSuggestionDraft(title="低糖梯度小试", purpose="验证糖含量与感官平衡", evidenceRefs=["input:brief"], validationItems=["总糖", "感官评分", "稳定性"])],
        evidenceRefs=["input:brief"],
    )


class FakeProvider:
    provider = "fake-local"; model = "qwen-test"
    def __init__(self, output=None, failure=None): self.output, self.failure, self.calls = output or valid_output(), failure, 0
    def innovate(self, context):
        self.calls += 1
        if self.failure: raise self.failure
        return self.output


def input_data() -> ProductInnovationInput:
    return ProductInnovationInput(brief="希望开发一款低糖、口感稳定的发酵饮品", industry="功能食品", targetMarket="中国", constraints=["仅作内部研发实验建议"])


def test_input_is_bounded() -> None:
    with pytest.raises(Exception):
        ProductInnovationInput(brief="x" * 5001)


def test_policy_rejects_unknown_evidence_and_forbidden_claims() -> None:
    policy = ProductInnovationPolicy()
    context = policy.build_context("exp-innovation", input_data(), [])
    unknown = valid_output().model_copy(update={"evidenceRefs": ["knowledge:missing"]})
    with pytest.raises(InnovationProviderFailure): policy.validate(context, unknown)
    forbidden = valid_output().model_copy(update={"valuePropositions": ["治疗疾病并直接上市"]})
    with pytest.raises(InnovationProviderFailure): policy.validate(context, forbidden)


def test_policy_rejects_final_formula_ratio_or_device_control() -> None:
    policy = ProductInnovationPolicy(); context = policy.build_context("exp-innovation", input_data(), [])
    ratio = valid_output().model_copy(update={"materialRoles": [InnovationMaterialRoleDraft(role="底物", purpose="原料比例 20%", constraints=[], evidenceRefs=["input:brief"])]})
    with pytest.raises(InnovationProviderFailure): policy.validate(context, ratio)
    control = valid_output().model_copy(update={"processConstraints": ["下发指令把温度设为 37°C"]})
    with pytest.raises(InnovationProviderFailure): policy.validate(context, control)


def test_agent_falls_back_adds_mandatory_boundaries_and_is_idempotent() -> None:
    provider = FakeProvider(failure=InnovationProviderFailure("providerDisabled"))
    agent = ProductInnovationAgent(provider=provider)
    first = agent.create_run("exp-innovation", "cmd-1", input_data())
    second = agent.create_run("exp-innovation", "cmd-1", input_data())
    assert first.runId == second.runId and provider.calls == 1
    assert first.mode == "rule_fallback"
    assert "研发实验建议" in " ".join(first.regulatoryConstraints)
    assert all("%" not in item.purpose for item in first.materialRoles)


def test_different_experiments_run_in_parallel() -> None:
    barrier = Barrier(2, timeout=1)
    class ParallelProvider(FakeProvider):
        def innovate(self, context): self.calls += 1; barrier.wait(); return self.output
    provider = ParallelProvider(); agent = ProductInnovationAgent(provider=provider)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(agent.create_run, exp, f"cmd-{exp}", input_data()) for exp in ("exp-a", "exp-b")]
        assert all(future.result().status == "completed" for future in futures)
    assert provider.calls == 2


def test_product_innovation_api_create_get_without_creating_formula(monkeypatch) -> None:
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.formula_service import formula_service
    from app.services.product_innovation_agent import product_innovation_agent
    product_innovation_agent._runs.clear(); product_innovation_agent._commands.clear()
    monkeypatch.setattr(product_innovation_agent, "provider", FakeProvider())
    before = set(formula_service._generated_results)
    client = TestClient(app)
    created = client.post("/experiments/exp-innovation-api/product-innovation-runs", json={"commandId": "api-1", "input": input_data().model_dump()})
    assert created.status_code == 200
    body = created.json()
    assert body["requiresHumanReview"] is True
    assert all("ratio" not in item and "%" not in item for item in body["materialRoles"] for item in [item["purpose"]])
    assert client.get(f"/experiments/exp-innovation-api/product-innovation-runs/{body['runId']}").json() == body
    assert client.get("/experiments/exp-innovation-api/product-innovation-runs/latest").json() == body
    assert client.get("/experiments/exp-innovation-api/product-innovation-runs/missing").status_code == 404
    assert set(formula_service._generated_results) == before


def test_local_provider_rejects_extra_ingredient_ratio_field() -> None:
    payload = valid_output().model_dump()
    payload["ingredientRatio"] = {"substrate": "20%"}
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"message": {"content": json.dumps(payload, ensure_ascii=False)}})))
    provider = LocalLlmProductInnovationProvider(provider="ollama", model="qwen", base_url="http://local", api_key="", enabled=True, client=client)
    context = ProductInnovationPolicy().build_context("exp-innovation", input_data(), [])
    with pytest.raises(InnovationProviderFailure) as error:
        provider.innovate(context)
    assert error.value.category == "invalidResponse"
