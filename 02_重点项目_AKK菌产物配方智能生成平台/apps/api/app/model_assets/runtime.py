from app.model_assets.service import ModelAssetCenterService
from app.model_evaluation.agent import model_evaluation_agent
from app.model_registry.runtime import feature_binding_store, promoted_model_inference_service
from app.research.service import promoted_model_registry
from app.services.experiment_service import experiment_service
from app.services.simulation_run_orchestrator import simulation_run_orchestrator
from app.enterprise_knowledge.runtime import enterprise_knowledge_usage_service


model_asset_center_service = ModelAssetCenterService(
    registry=promoted_model_registry,
    archive_provider=experiment_service.list_workspace_archive,
    evaluation_source=model_evaluation_agent,
    binding_store=feature_binding_store,
    simulation_source=simulation_run_orchestrator,
    artifact_store=promoted_model_inference_service.artifacts,
    knowledge_usage_source=enterprise_knowledge_usage_service,
)
