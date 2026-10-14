import pytest

from app.agent_registry.execution import AgentExecutionRegistry, AgentExecutionRegistrationError


def test_execution_registry_routes_actions_without_branching() -> None:
    registry = AgentExecutionRegistry()
    registry.register("simulationCreate", "simulation", lambda task: (3, "simulation-run-1"))
    assert registry.execute("simulationCreate", object()) == (3, "simulation-run-1")
    assert registry.agent_for("simulationCreate") == "simulation"


def test_execution_registry_rejects_duplicate_and_unknown_actions() -> None:
    registry = AgentExecutionRegistry()
    registry.register("advance", "dataAnalysisSupervisor", lambda task: (1, "run"))
    with pytest.raises(AgentExecutionRegistrationError, match="already registered"):
        registry.register("advance", "other", lambda task: (1, "run"))
    with pytest.raises(AgentExecutionRegistrationError, match="not registered"):
        registry.execute("missing", object())
