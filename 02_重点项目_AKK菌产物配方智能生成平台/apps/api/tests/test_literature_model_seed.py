from app.model_registry.inference import PromotedModelInferenceService
from app.model_registry.store import SqlitePromotedModelRegistry
from app.research.artifacts import ContentAddressedModelArtifactStore
from scripts.seed_literature_model import EXPERIMENT_ID, TARGET_FIELD, seed


def test_observed_seed_registers_reproducible_literature_baseline(tmp_path):
    artifacts_path = tmp_path / "artifacts"
    registry_path = tmp_path / "models.db"
    first = seed(artifact_root=artifacts_path, registry_path=registry_path)
    second = seed(artifact_root=artifacts_path, registry_path=registry_path)
    assert first.modelVersion == second.modelVersion
    assert first.modelCategory == "literature_baseline"
    assert first.datasetSnapshotId == "akk-food-grade-growth-figure2-v1"
    assert first.active is True
    inference = PromotedModelInferenceService(
        SqlitePromotedModelRegistry(registry_path),
        ContentAddressedModelArtifactStore(artifacts_path),
    )
    inputs = {"transfer_number": 3.0, "time_hours": 48.0}
    left = inference.predict_target(EXPERIMENT_ID, TARGET_FIELD, inputs)
    right = inference.predict_target(EXPERIMENT_ID, TARGET_FIELD, inputs)
    assert left.prediction == right.prediction
    assert left.datasetFingerprint == first.datasetFingerprint
