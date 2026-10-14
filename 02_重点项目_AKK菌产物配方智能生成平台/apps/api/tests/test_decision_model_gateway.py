import numpy as np
import pytest
from sklearn.linear_model import LinearRegression

from app.decision.errors import DecisionError
from app.decision.model_gateway import ActivatedModelGateway
from app.model_registry.contracts import PromotedModelRecord
from app.model_registry.inference import PromotedModelInferenceService
from app.model_registry.store import SqlitePromotedModelRegistry
from app.research.artifacts import ContentAddressedModelArtifactStore


def _gateway(tmp_path):
    registry = SqlitePromotedModelRegistry(tmp_path / "models.db")
    artifacts = ContentAddressedModelArtifactStore(tmp_path / "artifacts")
    x = np.asarray([[35.0], [36.0], [37.0], [38.0]])
    for index, (target, y) in enumerate(
        [
            ("target_product_output", [0.35, 0.51, 0.68, 0.73]),
            ("resource_consumption", [11.0, 12.0, 14.0, 17.0]),
        ],
        start=1,
    ):
        model = LinearRegression().fit(x, np.asarray(y))
        stored = artifacts.save(
            {
                "model": model,
                "featureNames": ["temperature_celsius"],
                "targetField": target,
            },
            {"target": target},
        )
        registry.register(
            PromotedModelRecord(
                modelVersion=f"decision-{index}",
                experimentId="decision-demo",
                campaignId="campaign",
                trialId=f"trial-{index}",
                artifactFingerprint=stored.fingerprint,
                artifactUri=stored.uri,
                datasetSnapshotId="observed-v1",
                datasetFingerprint="sha256:observed",
                dataManifestUri="data/decision/datasets/manifest.json",
                runnerKey="linear-regression",
                modelType="LinearRegression",
                modelCategory="literature_baseline",
                featureNames=["temperature_celsius"],
                targetField=target,
                targetUnit="relative_index",
                featureRanges={"temperature_celsius": {"min": 35, "max": 38}},
                metrics={"mae": 0.02, "r2": 0.91},
                uncertaintyMetric="mae",
                approvedBy="test",
                approvalReason="fixed observed test fixture",
                approvedAt=f"2026-07-25T0{index}:00:00+00:00",
            )
        )
    return ActivatedModelGateway(PromotedModelInferenceService(registry, artifacts))


def test_gateway_selects_a_separate_active_model_for_each_target(tmp_path):
    gateway = _gateway(tmp_path)
    features = {"temperature_celsius": 37.0}
    predictions = gateway.predict_many(
        "decision-demo",
        {
            "target_product_output": features,
            "resource_consumption": features,
        },
    )

    assert predictions["target_product_output"].lineage.targetField == "target_product_output"
    assert predictions["resource_consumption"].lineage.targetField == "resource_consumption"
    assert predictions["target_product_output"].lineage.modelVersion != predictions[
        "resource_consumption"
    ].lineage.modelVersion


def test_gateway_fails_when_target_model_is_missing(tmp_path):
    with pytest.raises(DecisionError, match="MODEL_NOT_AVAILABLE"):
        _gateway(tmp_path).predict("decision-demo", "unknown_target", {})


def test_gateway_blocks_out_of_range_inputs(tmp_path):
    with pytest.raises(DecisionError, match="MODEL_INPUT_OUT_OF_RANGE"):
        _gateway(tmp_path).predict(
            "decision-demo",
            "target_product_output",
            {"temperature_celsius": 999},
        )
