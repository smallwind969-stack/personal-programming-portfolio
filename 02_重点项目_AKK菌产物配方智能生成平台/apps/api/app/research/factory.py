from __future__ import annotations

import os

from app.research.artifacts import ContentAddressedModelArtifactStore
from app.research.runner import DeterministicMockResearchRunner, ResearchEvaluationRunner


def build_research_runner() -> tuple[ResearchEvaluationRunner, str | None]:
    requested = os.getenv("RESEARCH_RUNNER", "mock").strip().lower() or "mock"
    if requested == "mock": return DeterministicMockResearchRunner(), None
    if requested == "sklearn":
        try:
            from app.research.sklearn_runner import SklearnResearchRunner
            from app.services.feature_engineering_agent import feature_engineering_agent
            from app.services.experiment_file_service import experiment_file_service
            from app.feedback_retraining.dataset import (
                load_persisted_feedback_numeric_dataset,
            )
            root = os.getenv("RESEARCH_ARTIFACT_PATH", "data/runtime/model-artifacts").strip()

            def dataset_provider(experiment_id: str, dataset_id: str):
                if dataset_id.startswith("feedback-derived-dataset-"):
                    if experiment_file_service.store is None:
                        raise ValueError("persistent experiment data store is required for feedback retraining")
                    return load_persisted_feedback_numeric_dataset(
                        experiment_file_service.store, experiment_id, dataset_id,
                    )
                return feature_engineering_agent.export_numeric_training_dataset(
                    experiment_id, dataset_id,
                )

            return SklearnResearchRunner(
                dataset_provider,
                ContentAddressedModelArtifactStore(root),
            ), None
        except Exception as exc:
            return DeterministicMockResearchRunner(), f"sklearn runner initialization failed: {type(exc).__name__}"
    return DeterministicMockResearchRunner(), f"unsupported research runner: {requested}"
