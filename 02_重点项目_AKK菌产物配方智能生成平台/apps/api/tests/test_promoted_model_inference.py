import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

from app.model_registry.contracts import PromotedModelRecord
from app.model_registry.inference import PromotedModelInferenceService
from app.model_registry.store import SqlitePromotedModelRegistry
from app.research.artifacts import ContentAddressedModelArtifactStore


def setup_service(tmp_path):
    x = np.asarray([[35.0, 6.2], [36.0, 6.5], [37.0, 6.8], [38.0, 7.0], [39.0, 7.2]])
    y = np.asarray([0.3, 0.6, 1.1, 0.8, 0.4])
    model = GradientBoostingRegressor(random_state=42).fit(x, y)
    artifacts = ContentAddressedModelArtifactStore(tmp_path / "artifacts")
    stored = artifacts.save({"model": model, "featureNames": ["temperature", "ph"], "targetField": "od600"}, {"trusted": True})
    registry = SqlitePromotedModelRegistry(tmp_path / "models.db")
    registry.register(PromotedModelRecord(
        modelVersion="model-v1", experimentId="exp-real", campaignId="campaign-1", trialId="trial-1",
        artifactFingerprint=stored.fingerprint, artifactUri=stored.uri, datasetSnapshotId="snapshot-real",
        datasetFingerprint="sha256:dataset", runnerKey="sklearn-gradient-boosting-v1",
        modelType="GradientBoostingRegressor", featureNames=["temperature", "ph"], targetField="od600",
        featureRanges={"temperature": {"min": 35, "max": 39}, "ph": {"min": 6.2, "max": 7.2}},
        metrics={"mae": 0.1, "rmse": 0.15, "r2": 0.9}, approvedBy="owner", approvalReason="verified",
        approvedAt="2026-07-20T10:00:00+00:00",
    ))
    return PromotedModelInferenceService(registry, artifacts), stored


def test_inference_orders_named_features_and_returns_lineage(tmp_path) -> None:
    service, _ = setup_service(tmp_path)
    result = service.predict("exp-real", {"ph": 6.8, "temperature": 37.0})
    assert result.modelVersion == "model-v1"
    assert result.targetField == "od600" and result.prediction > 0.9
    assert result.extrapolated is False
    assert result.artifactFingerprint.startswith("sha256:")


def test_inference_rejects_missing_non_numeric_and_out_of_range_inputs(tmp_path) -> None:
    service, _ = setup_service(tmp_path)
    for inputs, message in [
        ({"temperature": 37.0}, "missing"),
        ({"temperature": "hot", "ph": 6.8}, "numeric"),
        ({"temperature": 45.0, "ph": 6.8}, "outside training range"),
    ]:
        try:
            service.predict("exp-real", inputs)
        except ValueError as exc:
            assert message in str(exc)
        else:
            raise AssertionError("invalid model input must be rejected")
    extrapolated = service.predict("exp-real", {"temperature": 45.0, "ph": 6.8}, allow_extrapolation=True)
    assert extrapolated.extrapolated is True
    assert extrapolated.outOfRangeFeatures == ["temperature"]


def test_inference_refuses_tampered_or_unregistered_artifact(tmp_path) -> None:
    service, stored = setup_service(tmp_path)
    with open(stored.localPath, "ab") as file:
        file.write(b"tampered")
    try:
        service.predict("exp-real", {"temperature": 37.0, "ph": 6.8})
    except ValueError as exc:
        assert "integrity" in str(exc)
    else:
        raise AssertionError("tampered artifact must not be loaded")
    try:
        service.predict("unknown", {"temperature": 37.0, "ph": 6.8})
    except LookupError as exc:
        assert "approved model" in str(exc)
    else:
        raise AssertionError("unregistered experiment must not infer")
