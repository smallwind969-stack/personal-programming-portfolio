import pytest
from fastapi.testclient import TestClient

from app.schemas.experiments import FeatureEngineeringConfig
from app.services.feature_engineering_agent import FeatureEngineeringAgent
from app.main import app
from app.routers import experiments as experiments_router


client = TestClient(app)


class SnapshotSource:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def get_latest_dataset_snapshot(self, experiment_id: str):
        assert experiment_id == self.snapshot.experimentId
        return self.snapshot


def snapshot(rows):
    from app.schemas.experiments import ExperimentDatasetSnapshot

    return ExperimentDatasetSnapshot(
        snapshotId="dataset-v1",
        experimentId="exp-feature",
        assetCount=1,
        mappingCount=4,
        alignedRowCount=len(rows),
        featureCount=3,
        anomalyCount=0,
        contentHash="snapshot-hash-v1",
        cleaningRunId="clean-v1",
        cleaningOutputHash="clean-hash-v1",
        alignedRows=rows,
        status="modeling_ready",
        createdAt="2026-07-20T00:00:00+00:00",
    )


def test_feature_run_calculates_history_only_features_and_audit(tmp_path) -> None:
    rows = [
        {"timestamp": f"2026-07-20T00:00:0{i}+00:00", "temperature_c": 36.0 + i, "ph": 7.0 - i * 0.1, "od600": 0.1 + i * 0.2}
        for i in range(5)
    ]
    source = SnapshotSource(snapshot(rows))
    agent = FeatureEngineeringAgent(source, store=None)

    run = agent.create_run("exp-feature", FeatureEngineeringConfig(
        targetField="od600",
        sourceFields=["temperature_c", "ph"],
        includeRaw=True,
        lagSteps=[1],
        rollingWindows=[3],
        includeDiff=True,
    ))

    assert run.status == "needsReview"
    assert run.targetField == "od600"
    assert "temperature_c_lag_1" in run.candidateFeatureNames
    assert "temperature_c_diff_1" in run.candidateFeatureNames
    assert "temperature_c_rolling_mean_3" in run.candidateFeatureNames
    assert run.featureRows[1]["temperature_c_lag_1"] == pytest.approx(36.0)
    assert run.featureRows[2]["temperature_c_diff_1"] == pytest.approx(1.0)
    # The value at index 2 may only use indices 0..2, never index 3 or 4.
    assert run.featureRows[2]["temperature_c_rolling_mean_3"] == pytest.approx(37.0)
    definition = next(item for item in run.definitions if item.name == "temperature_c_rolling_mean_3")
    assert definition.formula == "mean(temperature_c[t-2:t])"
    assert not any(issue.severity == "blocking" for issue in run.leakageIssues)


def test_target_leakage_and_invalid_future_windows_are_rejected(tmp_path) -> None:
    source = SnapshotSource(snapshot([
        {"timestamp": "2026-07-20T00:00:00+00:00", "temperature_c": 37.0, "od600": 0.3},
        {"timestamp": "2026-07-20T00:01:00+00:00", "temperature_c": 38.0, "od600": 0.5},
    ]))
    agent = FeatureEngineeringAgent(source, store=None)

    with pytest.raises(ValueError, match="target"):
        agent.create_run("exp-feature", FeatureEngineeringConfig(
            targetField="od600", sourceFields=["temperature_c", "od600"],
        ))
    with pytest.raises(ValueError):
        FeatureEngineeringConfig(
            targetField="od600", sourceFields=["temperature_c"], lagSteps=[-1],
        )


def test_human_confirmation_is_required_and_snapshot_change_makes_run_stale(tmp_path) -> None:
    source = SnapshotSource(snapshot([
        {"timestamp": "2026-07-20T00:00:00+00:00", "temperature_c": 37.0, "od600": 0.3},
        {"timestamp": "2026-07-20T00:01:00+00:00", "temperature_c": 38.0, "od600": 0.5},
        {"timestamp": "2026-07-20T00:02:00+00:00", "temperature_c": 39.0, "od600": 0.8},
    ]))
    agent = FeatureEngineeringAgent(source, store=None)
    run = agent.create_run("exp-feature", FeatureEngineeringConfig(
        targetField="od600", sourceFields=["temperature_c"], lagSteps=[1],
        rollingWindows=[], includeDiff=False,
    ))

    with pytest.raises(ValueError, match="human confirmation"):
        agent.assert_training_ready("exp-feature")
    with pytest.raises(ValueError, match="reason"):
        agent.confirm("exp-feature", run.featureSetId, "owner", "", ["temperature_c_lag_1"])
    confirmed = agent.confirm(
        "exp-feature", run.featureSetId, "owner", "用于首轮时序回归",
        ["temperature_c_lag_1"],
    )
    assert confirmed.status == "confirmed"
    assert confirmed.selectedFeatureNames == ["temperature_c_lag_1"]
    assert agent.assert_training_ready("exp-feature").featureSetId == run.featureSetId

    source.snapshot = source.snapshot.model_copy(update={"contentHash": "snapshot-hash-v2"})
    with pytest.raises(ValueError, match="stale"):
        agent.assert_training_ready("exp-feature")


def test_feature_set_recovers_after_restart_and_exports_confirmed_matrix(tmp_path) -> None:
    from app.services.experiment_data_store import SqliteExperimentDataStore

    rows = [
        {"timestamp": f"2026-07-20T00:00:0{i}+00:00", "temperature_c": 36.0 + i, "ph": 7.0 - i * 0.1, "od600": 0.1 + i * 0.2}
        for i in range(5)
    ]
    source = SnapshotSource(snapshot(rows))
    store = SqliteExperimentDataStore(tmp_path / "data.db", tmp_path / "objects")
    first = FeatureEngineeringAgent(source, store)
    run = first.create_run("exp-feature", FeatureEngineeringConfig(
        targetField="od600", sourceFields=["temperature_c", "ph"],
        lagSteps=[1], rollingWindows=[], includeDiff=False,
    ))
    first.confirm(
        "exp-feature", run.featureSetId, "owner", "确认历史滞后变量",
        ["temperature_c_lag_1", "ph_lag_1"],
    )

    recovered = FeatureEngineeringAgent(source, store)
    ready = recovered.assert_training_ready("exp-feature")
    dataset = recovered.export_numeric_training_dataset("exp-feature", "dataset-v1")

    assert ready.status == "confirmed"
    assert dataset.featureNames == ["temperature_c_lag_1", "ph_lag_1"]
    assert dataset.targetField == "od600"
    assert dataset.X.shape == (4, 2)
    assert dataset.y.shape == (4,)
    assert ready.outputHash in dataset.datasetFingerprint


def test_feature_engineering_api_create_list_and_confirm(monkeypatch) -> None:
    rows = [
        {"timestamp": f"2026-07-20T00:00:0{i}+00:00", "temperature_c": 36.0 + i, "od600": 0.1 + i * 0.2}
        for i in range(4)
    ]
    agent = FeatureEngineeringAgent(SnapshotSource(snapshot(rows)), store=None)
    monkeypatch.setattr(experiments_router, "feature_engineering_agent", agent)

    created = client.post("/experiments/exp-feature/feature-engineering-runs", json={
        "targetField": "od600",
        "sourceFields": ["temperature_c"],
        "includeRaw": True,
        "lagSteps": [1],
        "rollingWindows": [],
        "includeDiff": False,
    })
    assert created.status_code == 200
    feature_set_id = created.json()["featureSetId"]
    assert created.json()["status"] == "needsReview"

    listed = client.get("/experiments/exp-feature/feature-engineering-runs")
    assert listed.status_code == 200 and len(listed.json()) == 1

    confirmed = client.post(
        f"/experiments/exp-feature/feature-engineering-runs/{feature_set_id}/confirm",
        json={
            "operator": "研发负责人",
            "reason": "确认温度历史值用于建模",
            "selectedFeatureNames": ["temperature_c", "temperature_c_lag_1"],
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    assert confirmed.json()["confirmedBy"] == "研发负责人"
