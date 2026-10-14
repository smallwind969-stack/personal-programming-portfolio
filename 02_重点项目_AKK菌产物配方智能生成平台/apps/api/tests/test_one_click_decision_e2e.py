from pathlib import Path

from app.auth.contracts import UserRole
from app.auth.service import SqliteAuthService
from app.decision.knowledge_repository import JsonKnowledgeRepository
from app.decision.model_gateway import ActivatedModelGateway
from app.decision.pipeline import DecisionPipeline
from app.decision.trace_store import SqliteDecisionTraceStore
from app.model_registry.inference import PromotedModelInferenceService
from app.model_registry.store import SqlitePromotedModelRegistry
from app.research.artifacts import ContentAddressedModelArtifactStore
from scripts.seed_literature_model import EXPERIMENT_ID, seed


def _pipeline(tmp_path):
    artifact_root = tmp_path / "artifacts"
    registry_path = tmp_path / "models.db"
    seed(artifact_root=artifact_root, registry_path=registry_path)
    auth = SqliteAuthService(tmp_path / "auth.db")
    auth.seed_user(
        username="admin",
        password="Strong-password-2026!",
        display_name="菌藻启元管理员",
        tenant_id="tenant-junzao-qiyuan",
        role=UserRole.tenant_admin,
    )
    identity = auth.resolve_token(
        auth.login("admin", "Strong-password-2026!").accessToken
    )
    pipeline = DecisionPipeline(
        JsonKnowledgeRepository(Path("data/decision/knowledge-v1.json")),
        ActivatedModelGateway(
            PromotedModelInferenceService(
                SqlitePromotedModelRegistry(registry_path),
                ContentAddressedModelArtifactStore(artifact_root),
            )
        ),
        SqliteDecisionTraceStore(tmp_path / "traces.db", auth),
        model_experiment_id=EXPERIMENT_ID,
    )
    return pipeline, identity


def _payload():
    return {
        "rawRequirement": "开发一款低糖、高弹性、具有抗氧化能力的菌藻果冻",
        "requirement": {
            "productType": "功能性果冻",
            "attributes": [
                {"metric": "target_product_output", "direction": "maximize"}
            ],
            "missingConstraints": [],
            "confidence": 0.95,
        },
        "supplementalConstraints": {
            "minimumOutput": 0.2,
            "minimumQuality": 0.2,
        },
    }


def test_real_registered_model_runs_three_plan_trace_and_confirmation(tmp_path):
    pipeline, identity = _pipeline(tmp_path)
    first = pipeline.execute(identity, _payload())
    second = pipeline.execute(identity, _payload())
    assert len(first.plans) == 3
    assert [plan["objective"] for plan in first.plans] == [
        "maximize_output",
        "balanced",
        "minimize_resource",
    ]
    assert first.plans == second.plans
    assert first.knowledgeIds
    assert first.dataVersions == ["akk-food-grade-growth-figure2-v1"]
    assert first.modelVersions["target_product_output"].startswith(
        "literature-od600-"
    )
    confirmed = pipeline.confirm(
        identity,
        first.runId,
        first.plans[1]["planId"],
        "批准作为竞赛标准案例",
    )
    assert confirmed.confirmationStatus == "confirmed"
    assert pipeline.get(identity, first.runId).confirmation is not None


def test_new_decision_module_has_no_mock_repository_dependency():
    for path in Path("apps/api/app/decision").glob("*.py"):
        assert "MockRepository" not in path.read_text(encoding="utf-8")
