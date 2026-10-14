from app.model_evaluation.agent import model_evaluation_agent
from app.research.service import promoted_model_registry
from app.research_reports.service import ResearchReportService
from app.services.experiment_file_service import experiment_file_service
from app.services.experiment_service import experiment_service
from app.services.optimization_orchestrator import optimization_orchestrator
from app.services.simulation_run_orchestrator import simulation_run_orchestrator


research_report_service = ResearchReportService(
    store=experiment_file_service.store,
    workspace_source=experiment_service,
    dataset_source=experiment_file_service,
    model_registry=promoted_model_registry,
    evaluation_source=model_evaluation_agent,
    simulation_source=simulation_run_orchestrator,
    optimization_source=optimization_orchestrator,
)
