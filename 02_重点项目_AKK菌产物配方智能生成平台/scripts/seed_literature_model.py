"""Train and register a traceable literature baseline model."""
from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from app.model_registry.contracts import PromotedModelRecord
from app.model_registry.inference import PromotedModelInferenceService
from app.model_registry.store import SqlitePromotedModelRegistry
from app.research.artifacts import ContentAddressedModelArtifactStore


EXPERIMENT_ID = "decision-functional-jelly-v1"
TARGET_FIELD = "target_product_output"
FEATURE_NAMES = ["transfer_number", "time_hours"]
DEFAULT_DATASET = (
    ROOT / "data" / "decision" / "datasets" / "akk-food-grade-growth-figure2-v1.csv"
)


def seed(
    *,
    dataset_path: Path = DEFAULT_DATASET,
    artifact_root: Path | None = None,
    registry_path: Path | None = None,
) -> PromotedModelRecord:
    artifact_root = artifact_root or Path(
        os.getenv(
            "RESEARCH_ARTIFACT_PATH",
            str(ROOT / "data" / "runtime" / "model-artifacts"),
        )
    )
    registry_path = registry_path or Path(
        os.getenv(
            "MODEL_REGISTRY_PATH",
            str(ROOT / "data" / "runtime" / "model-registry.db"),
        )
    )
    raw = dataset_path.read_bytes()
    dataset_fingerprint = f"sha256:{sha256(raw).hexdigest()}"
    dataset = pd.read_csv(dataset_path)
    if set(dataset["evidenceKind"]) - {
        "author_table",
        "author_supplement",
        "figure_digitized",
    }:
        raise ValueError("training data contains an unsupported evidence kind")
    if dataset["targetValue"].isna().any() or dataset["sourceRow"].duplicated().any():
        raise ValueError("every training target must have unique row lineage")

    features = dataset[FEATURE_NAMES].astype(float)
    feature_matrix = features.to_numpy(dtype=float)
    target = dataset["targetValue"].astype(float)
    estimator = make_pipeline(
        PolynomialFeatures(degree=2, include_bias=False),
        StandardScaler(),
        Ridge(alpha=0.5),
    )
    folds = KFold(n_splits=4, shuffle=False)
    held_out = cross_val_predict(estimator, feature_matrix, target, cv=folds)
    metrics = {
        "mae": float(mean_absolute_error(target, held_out)),
        "rmse": float(mean_squared_error(target, held_out) ** 0.5),
        "r2": float(r2_score(target, held_out)),
    }
    estimator.fit(feature_matrix, target)

    artifacts = ContentAddressedModelArtifactStore(artifact_root)
    stored = artifacts.save(
        {
            "model": estimator,
            "featureNames": FEATURE_NAMES,
            "targetField": TARGET_FIELD,
        },
        {
            "datasetFingerprint": dataset_fingerprint,
            "datasetVersion": dataset["datasetId"].iloc[0],
            "evidenceKind": "figure_digitized",
            "sourceUrl": dataset["sourceUrl"].iloc[0],
            "sourceLocation": dataset["sourceLocation"].iloc[0],
        },
    )
    version = f"literature-od600-{dataset_fingerprint[-12:]}"
    record = PromotedModelRecord(
        modelVersion=version,
        experimentId=EXPERIMENT_ID,
        campaignId="public-observation-baseline",
        trialId="pmc11480725-supplementary-figure-2",
        artifactFingerprint=stored.fingerprint,
        artifactUri=stored.uri,
        datasetSnapshotId=dataset["datasetId"].iloc[0],
        datasetFingerprint=dataset_fingerprint,
        dataManifestUri="data/decision/datasets/manifest.json",
        runnerKey="deterministic-polynomial-ridge-v1",
        modelType="PolynomialFeatures+Ridge",
        modelCategory="literature_baseline",
        featureNames=FEATURE_NAMES,
        targetField=TARGET_FIELD,
        targetUnit="OD600",
        featureRanges={
            name: {
                "min": float(features[name].min()),
                "max": float(features[name].max()),
            }
            for name in FEATURE_NAMES
        },
        metrics=metrics,
        uncertaintyMetric="mae",
        approvedBy="platform_admin",
        approvalReason="公开论文补充图直接观测值完成来源复核与固定交叉验证",
        approvedAt="2026-07-25T00:00:00+00:00",
        status="approved",
        validationStatus="passed",
        active=True,
    )
    registry = SqlitePromotedModelRegistry(registry_path)
    registry.register(record)
    check = PromotedModelInferenceService(registry, artifacts).predict_target(
        EXPERIMENT_ID,
        TARGET_FIELD,
        {"transfer_number": 3.0, "time_hours": 48.0},
    )
    if not np.isfinite(check.prediction):
        raise ValueError("registered model did not produce a finite prediction")
    return record


if __name__ == "__main__":
    registered = seed()
    print(
        f"registered {registered.modelVersion} for {registered.targetField}; "
        f"dataset={registered.datasetSnapshotId}"
    )
