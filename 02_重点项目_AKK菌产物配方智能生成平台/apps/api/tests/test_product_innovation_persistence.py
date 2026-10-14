from app.product_innovation.contracts import (
    InnovationMaterialRoleDraft, InnovationMetricDraft, InnovationProviderOutput,
    InnovationSuggestionDraft, ProductInnovationInput, ProductRequirementConfirmRequest,
)
from app.product_innovation.store import SqliteProductInnovationStore
from app.services.product_innovation_agent import ProductInnovationAgent
from app.services.product_requirement_registry import ProductRequirementRegistry


class Provider:
    provider = "test"
    model = "test-model"

    def innovate(self, _context):
        return InnovationProviderOutput(
            workingName="低糖培养产物", category="生物制造", problemStatement="验证低糖目标与培养稳定性。",
            targetUserTags=["研发人员"], usageScenarios=["小试"], valuePropositions=["可验证"],
            targetMetrics=[InnovationMetricDraft(metricName="总糖", direction="decrease", unit="g/L", targetDescription="相对基线下降", evidenceRefs=["input:brief"])],
            materialRoles=[InnovationMaterialRoleDraft(role="培养底物", purpose="支持培养过程", constraints=["可追溯"], evidenceRefs=["input:brief"])],
            costAssumptions=["报价后确认"], processConstraints=["先完成小试"], regulatoryConstraints=["研发实验建议"],
            risks=["目标间可能存在权衡"], unresolvedQuestions=["目标阈值待确认"],
            validationPlan=[InnovationSuggestionDraft(title="梯度验证", purpose="验证目标", evidenceRefs=["input:brief"], validationItems=["总糖"])],
            evidenceRefs=["input:brief"],
        )


def test_innovation_run_and_confirmed_requirement_survive_service_restart(tmp_path) -> None:
    path = tmp_path / "product-innovation.db"
    first_store = SqliteProductInnovationStore(path)
    first_agent = ProductInnovationAgent(Provider(), run_store=first_store)
    first_registry = ProductRequirementRegistry(first_agent, store=first_store)
    run = first_agent.create_run(
        "exp-persist", "create-1",
        ProductInnovationInput(brief="开发低糖且培养稳定的通用生物制造产物"),
    )
    version = first_registry.confirm(
        "exp-persist", run.runId,
        ProductRequirementConfirmRequest(commandId="confirm-1", operator="负责人", reason="确认进入建模"),
    )

    second_store = SqliteProductInnovationStore(path)
    second_agent = ProductInnovationAgent(Provider(), run_store=second_store)
    second_registry = ProductRequirementRegistry(second_agent, store=second_store)

    assert second_agent.get_run("exp-persist", run.runId) == run
    restored = second_registry.latest("exp-persist")
    assert restored is not None
    assert restored.requirementVersionId == version.requirementVersionId
    assert restored.sourceRunId == run.runId
