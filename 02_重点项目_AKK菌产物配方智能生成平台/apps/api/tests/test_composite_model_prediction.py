import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

from app.model_registry.bindings import FeatureBindingEntry, FeatureBindingVersion, SimulationFeatureBindingService, SqliteFeatureBindingStore
from app.model_registry.composite import CompositeModelPredictionService
from app.model_registry.contracts import PromotedModelRecord
from app.model_registry.inference import PromotedModelInferenceService
from app.model_registry.store import SqlitePromotedModelRegistry
from app.research.artifacts import ContentAddressedModelArtifactStore


def setup_composite(tmp_path):
    artifacts = ContentAddressedModelArtifactStore(tmp_path / "artifacts")
    registry = SqlitePromotedModelRegistry(tmp_path / "models.db")
    binding_store = SqliteFeatureBindingStore(tmp_path / "bindings.db")
    binding_service = SimulationFeatureBindingService(binding_store)
    x = np.asarray([[35, 6.2], [36, 6.5], [37, 6.8], [38, 7.0], [39, 7.2]], dtype=float)
    for index, (target, values, rmse) in enumerate([
        ("optical_density_600", [0.2, 0.5, 1.1, 0.7, 0.3], 0.1),
        ("scfa_score", [30, 45, 75, 60, 35], 4.0),
    ], start=1):
        model = GradientBoostingRegressor(random_state=42).fit(x, np.asarray(values))
        stored = artifacts.save({"model": model, "featureNames": ["temperature_c", "ph"], "targetField": target}, {"target": target})
        version = f"model-v{index}"
        registry.register(PromotedModelRecord(
            modelVersion=version, experimentId="exp-real", campaignId=f"c{index}", trialId=f"t{index}",
            artifactFingerprint=stored.fingerprint, artifactUri=stored.uri, datasetSnapshotId=f"s{index}",
            datasetFingerprint=f"sha256:data{index}", runnerKey="sklearn-gradient-boosting-v1", modelType="GradientBoostingRegressor",
            featureNames=["temperature_c", "ph"], targetField=target,
            featureRanges={"temperature_c": {"min": 35, "max": 39}, "ph": {"min": 6.2, "max": 7.2}},
            metrics={"r2": 0.88, "mae": rmse / 2, "rmse": rmse}, approvedBy="owner", approvalReason="verified",
            approvedAt=f"2026-07-20T1{index}:00:00+00:00",
        ))
        binding_service.confirm(FeatureBindingVersion(
            bindingVersion=f"binding-v{index}", experimentId="exp-real", modelVersion=version,
            featureNames=["temperature_c", "ph"], entries=[
                FeatureBindingEntry(modelFeature="temperature_c", standardField="temperature_c", simulationParameter="temperatureC"),
                FeatureBindingEntry(modelFeature="ph", standardField="ph", simulationParameter="ph"),
            ], confirmedBy="owner", confirmationReason="verified mapping", createdAt=f"2026-07-20T1{index}:30:00+00:00",
        ))
    service = CompositeModelPredictionService(
        registry, binding_service, PromotedModelInferenceService(registry, artifacts),
    )
    return service, registry


def test_registry_returns_latest_approved_model_per_target(tmp_path) -> None:
    _, registry = setup_composite(tmp_path)
    assert registry.latest_by_target("exp-real", "scfa_score").modelVersion == "model-v2"
    assert registry.latest_by_target("exp-real", "missing") is None


def test_composite_prediction_combines_targets_intervals_and_lineage(tmp_path) -> None:
    service, _ = setup_composite(tmp_path)
    result = service.predict(
        "exp-real", {"temperatureC": 37.0, "ph": 6.8},
        ["optical_density_600", "scfa_score", "barrier_score"],
    )
    assert len(result.targets) == 2 and result.unavailableTargets == ["barrier_score"]
    od = next(item for item in result.targets if item.targetField == "optical_density_600")
    assert od.modelVersion == "model-v1" and od.bindingVersion == "binding-v1"
    assert od.interval.method == "approximate95_rmse" and od.interval.upper > od.prediction > od.interval.lower
    assert result.reliability == "high" and result.predictionSource == "promoted_model_composite"
