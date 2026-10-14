from app.model_registry.contracts import PromotedModelRecord
from app.model_registry.store import SqlitePromotedModelRegistry


def record(version: str = "model-researchExperiment-v1", approved_at: str = "2026-07-20T10:00:00+00:00") -> PromotedModelRecord:
    return PromotedModelRecord(
        modelVersion=version, experimentId="exp-real", campaignId="campaign-1", trialId="trial-1",
        artifactFingerprint="sha256:" + "a" * 64, artifactUri="artifact://models/" + "a" * 64,
        datasetSnapshotId="snapshot-real", datasetFingerprint="sha256:dataset", runnerKey="sklearn-gradient-boosting-v1",
        modelType="GradientBoostingRegressor", featureNames=["temperature", "ph"], targetField="od600",
        featureRanges={"temperature": {"min": 35.0, "max": 39.0}, "ph": {"min": 6.2, "max": 7.2}},
        metrics={"mae": 0.1, "rmse": 0.15, "r2": 0.9}, approvedBy="研发负责人",
        approvalReason="指标通过且完成人工复核", approvedAt=approved_at,
    )


def test_registry_persists_versions_and_returns_latest_approved(tmp_path) -> None:
    registry = SqlitePromotedModelRegistry(tmp_path / "models.db")
    registry.register(record())
    registry.register(record("model-researchExperiment-v2", "2026-07-20T11:00:00+00:00"))
    latest = registry.latest("exp-real")
    assert latest and latest.modelVersion == "model-researchExperiment-v2"
    assert registry.get("exp-real", "model-researchExperiment-v1").targetField == "od600"


def test_registry_is_idempotent_but_rejects_version_reuse_with_different_lineage(tmp_path) -> None:
    registry = SqlitePromotedModelRegistry(tmp_path / "models.db")
    first = record(); assert registry.register(first) == first
    assert registry.register(first) == first
    changed = first.model_copy(update={"trialId": "trial-other"})
    try:
        registry.register(changed)
    except ValueError as exc:
        assert "different lineage" in str(exc)
    else:
        raise AssertionError("model version reuse must be rejected")
