"""Shared promoted-model runtime used by both API routes and domain orchestrators."""

import os

from app.model_registry.bindings import SimulationFeatureBindingService, SqliteFeatureBindingStore
from app.model_registry.composite import CompositeModelPredictionService
from app.model_registry.inference import PromotedModelInferenceService
from app.research.artifacts import ContentAddressedModelArtifactStore
from app.research.service import promoted_model_registry
from app.paths import project_path


promoted_model_inference_service = PromotedModelInferenceService(
    promoted_model_registry,
    ContentAddressedModelArtifactStore(
        project_path(os.getenv("RESEARCH_ARTIFACT_PATH", "data/runtime/model-artifacts"))
    ),
)
feature_binding_store = SqliteFeatureBindingStore(
    project_path(os.getenv("FEATURE_BINDING_STORE_PATH", "data/runtime/feature-bindings.db"))
)
feature_binding_service = SimulationFeatureBindingService(feature_binding_store)
composite_prediction_service = CompositeModelPredictionService(
    promoted_model_registry,
    feature_binding_service,
    promoted_model_inference_service,
)
