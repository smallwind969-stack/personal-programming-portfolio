from __future__ import annotations

from collections.abc import Callable
from typing import Any


class AgentExecutionRegistrationError(RuntimeError):
    pass


class AgentExecutionRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, tuple[str, Callable[[Any], tuple[int, str]]]] = {}

    def register(self, action: str, agent_key: str, handler: Callable[[Any], tuple[int, str]]) -> None:
        if action in self._handlers:
            raise AgentExecutionRegistrationError(f"action {action} already registered")
        self._handlers[action] = (agent_key, handler)

    def execute(self, action: str, task: Any) -> tuple[int, str]:
        if action not in self._handlers:
            raise AgentExecutionRegistrationError(f"action {action} is not registered")
        return self._handlers[action][1](task)

    def agent_for(self, action: str) -> str:
        if action not in self._handlers:
            raise AgentExecutionRegistrationError(f"action {action} is not registered")
        return self._handlers[action][0]

    @property
    def actions(self) -> list[str]:
        return sorted(self._handlers)


def build_execution_registry(orchestrator, simulation, optimization, research=None, binding_advisor=None) -> AgentExecutionRegistry:
    if research is None:
        from app.research.service import research_campaign_service
        research = research_campaign_service
    if binding_advisor is None:
        from app.services.feature_binding_advisor_agent import feature_binding_advisor
        binding_advisor = feature_binding_advisor
    registry = AgentExecutionRegistry()

    def data_advance(task):
        run = orchestrator.advance(task.experimentId, task.runId, task.expectedRevision, task.commandId)
        return run.runtimeRevision, run.runId

    def data_stop(task):
        run = orchestrator.stop(task.experimentId, task.runId, expected_revision=task.expectedRevision, command_id=task.commandId)
        return run.runtimeRevision, run.runId

    registry.register("advance", "dataAnalysisSupervisor", data_advance)
    registry.register("stop", "dataAnalysisSupervisor", data_stop)
    registry.register("simulationCreate", "simulation", lambda task: _versioned(simulation.create(task.experimentId)))
    registry.register("simulationAdvance", "simulation", lambda task: _versioned(simulation.advance(task.experimentId, task.runId)))
    registry.register("simulationStop", "simulation", lambda task: _versioned(simulation.stop(task.experimentId, task.runId)))
    registry.register("simulationRetry", "simulation", lambda task: _versioned(simulation.retry(task.experimentId, task.runId)))
    registry.register("optimizationCreate", "optimization", lambda task: _versioned(optimization.create(task.experimentId)))
    registry.register("optimizationSubmit", "optimization", lambda task: _versioned(optimization.submit(task.experimentId, task.runId)))
    registry.register("optimizationAdvance", "optimization", lambda task: _versioned(optimization.advance(task.experimentId, task.runId)))
    registry.register("researchTrial", "researchExperiment", lambda task: _research_trial(research, task))
    registry.register("featureBindingSuggest", "featureBindingAdvisor", lambda task: _binding_suggestion(binding_advisor, task))
    return registry


def _versioned(run) -> tuple[int, str]:
    return run.version, run.runId


def _research_trial(service, task) -> tuple[int, str]:
    from app.research.contracts import ResearchTrialCreate
    trial = service.run_trial(task.experimentId, task.runId, ResearchTrialCreate(
        commandId=task.commandId, hypothesis=task.payload["hypothesis"], parameterPatch=task.payload["parameterPatch"],
    ))
    return trial.sequence, task.runId


def _binding_suggestion(advisor, task) -> tuple[int, str]:
    from app.feature_binding_advisor.contracts import DeviceAdapterPackSelector
    raw_selector = task.payload.get("adapterPack")
    selector = DeviceAdapterPackSelector.model_validate(raw_selector) if raw_selector else None
    run = advisor.create_run(task.experimentId, task.runId, task.commandId, selector)
    return max(1, run.candidateCount), run.runId
