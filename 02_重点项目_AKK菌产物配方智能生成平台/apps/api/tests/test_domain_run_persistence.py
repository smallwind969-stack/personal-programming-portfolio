from app.services.domain_run_store import SqliteDomainRunStore
from app.services.simulation_run_orchestrator import SimulationRunOrchestrator
from app.services.optimization_orchestrator import OptimizationOrchestrator
from app.schemas.simulation import ExperimentSimulationRun
from app.schemas.optimization import ExperimentOptimizationRun


def test_simulation_run_is_visible_and_mutable_across_instances(tmp_path) -> None:
    path = tmp_path / "domains.db"
    first = SimulationRunOrchestrator(SqliteDomainRunStore(path, "simulation", ExperimentSimulationRun))
    created = first.create("exp-food-012")
    second = SimulationRunOrchestrator(SqliteDomainRunStore(path, "simulation", ExperimentSimulationRun))
    assert second.latest("exp-food-012").runId == created.runId
    advanced = second.advance("exp-food-012", created.runId)
    assert first.latest("exp-food-012").progressPercent == advanced.progressPercent


def test_optimization_run_selection_is_visible_across_instances(tmp_path) -> None:
    path = tmp_path / "domains.db"
    first = OptimizationOrchestrator(SqliteDomainRunStore(path, "optimization", ExperimentOptimizationRun))
    created = first.create("exp-food-012")
    selected = created.candidatePlans[0]
    first.select("exp-food-012", created.runId, selected.planId, selected.parameters)
    second = OptimizationOrchestrator(SqliteDomainRunStore(path, "optimization", ExperimentOptimizationRun))
    restored = second.latest("exp-food-012")
    assert restored.selectedPlanId == selected.planId
    assert restored.editedParameters == selected.parameters
