import pytest
from fastapi.testclient import TestClient

from app.agent_registry.builtin import build_builtin_catalog
from app.agent_registry.models import AgentManifest, WorkflowManifest, WorkflowNodeManifest
from app.agent_registry.registry import AgentCatalog, AgentCatalogValidationError
from app.main import app


def test_builtin_catalog_has_versioned_specialists_and_valid_workflows() -> None:
    catalog = build_builtin_catalog()
    snapshot = catalog.snapshot()
    keys = {agent.agentKey for agent in snapshot.agents}
    assert len(keys) >= 12
    assert {"dataCollectionLocalization", "schemaRecognition", "featureBindingAdvisor", "modeling", "researchExperiment", "modelEvaluation", "resultInterpretation", "productInnovation", "simulation", "optimization"} <= keys
    assert all(agent.version.startswith("1.") for agent in snapshot.agents)
    assert all(agent.inputSchema and agent.outputSchema and agent.description for agent in snapshot.agents)
    assert {workflow.workflowKey for workflow in snapshot.workflows} >= {"experiment-data-analysis", "experiment-rd-loop", "enterprise-device-adaptation"}
    adaptation = catalog.workflow("enterprise-device-adaptation")
    assert [node.agentKey for node in adaptation.nodes] == ["schemaRecognition", "featureBindingAdvisor", "humanReview"]
    assert adaptation.nodes[-1].requiresHuman is True


def test_catalog_rejects_missing_agent_and_cycle() -> None:
    catalog = AgentCatalog()
    catalog.register_agent(AgentManifest(
        agentKey="known", version="1.0.0", displayName="Known", description="known agent",
        capabilities=["test"], requiredWorkerCapabilities=["cpu"], inputSchema="Input", outputSchema="Output",
    ))
    with pytest.raises(AgentCatalogValidationError, match="missing"):
        catalog.register_workflow(WorkflowManifest(
            workflowKey="bad-missing", version="1.0.0", displayName="bad",
            nodes=[WorkflowNodeManifest(nodeId="a", agentKey="missing", stageLabel="A")], edges={}, entryNodeId="a",
        ))
    with pytest.raises(AgentCatalogValidationError, match="cycle"):
        catalog.register_workflow(WorkflowManifest(
            workflowKey="bad-cycle", version="1.0.0", displayName="bad",
            nodes=[WorkflowNodeManifest(nodeId="a", agentKey="known", stageLabel="A"), WorkflowNodeManifest(nodeId="b", agentKey="known", stageLabel="B")],
            edges={"a": ["b"], "b": ["a"]}, entryNodeId="a",
        ))


def test_runtime_catalog_api_exposes_framework_and_safety_boundary() -> None:
    response = TestClient(app).get("/agent-runtime/catalog")
    assert response.status_code == 200
    body = response.json()
    assert body["framework"] == "langgraph"
    assert body["agentCount"] == len(body["agents"])
    assert body["workflowCount"] == len(body["workflows"])
    assert body["disclaimer"] == "研发实验建议"
    assert all("requiredWorkerCapabilities" in agent for agent in body["agents"])


def test_data_analysis_workflow_drives_runtime_graph_definition() -> None:
    from app.services.agent_orchestrator import AgentOrchestrator

    definition = AgentOrchestrator._graph_definition()
    workflow = build_builtin_catalog().workflow("experiment-data-analysis")
    assert [node.nodeId for node in definition.nodes] == [node.nodeId for node in workflow.nodes]
    assert definition.entryNodeId == workflow.entryNodeId
