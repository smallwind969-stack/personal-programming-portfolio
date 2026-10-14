import pytest
from fastapi.testclient import TestClient

from app.feature_binding_advisor.adapter_pack import (
    DeviceAdapterEntry, DeviceAdapterPackCreate, DeviceAdapterPackService, SqliteDeviceAdapterPackStore,
)
from app.repositories.sqlite_repository import SqliteRepository
from app.schemas.experiments import (
    CleaningAlignmentConfig,
    ExperimentConfirmFieldMappingsRequest,
    ExperimentConfirmedFieldMapping,
    ExperimentCreateRequest,
    ExperimentTextFileUploadRequest,
)
from app.services.cleaning_alignment_agent import CleaningAlignmentAgent
from app.services.data_collection_localization_agent import DataCollectionLocalizationAgent
from app.services.experiment_data_store import SqliteExperimentDataStore
from app.services.experiment_file_service import ExperimentFileService
from app.services.experiment_service import ExperimentService
from app.main import app
from app.routers import experiments as experiments_router

client = TestClient(app)


def setup_pipeline(tmp_path, content: str):
    store = SqliteExperimentDataStore(tmp_path / "data.db", tmp_path / "objects")
    files = ExperimentFileService(store)
    workspaces = ExperimentService(SqliteRepository(tmp_path / "platform.db"))
    packs = DeviceAdapterPackService(SqliteDeviceAdapterPackStore(tmp_path / "packs.db"))
    pack = packs.export(DeviceAdapterPackCreate(
        enterpriseKey="enterprise-a", deviceType="reactor-x", packVersion="1.0.0",
        createdBy="owner", entries=[DeviceAdapterEntry(
            sourceFieldAlias="TempF", standardField="temperature_c",
            simulationParameter="temperatureC", sourceUnit="F", targetUnit="C",
            scale=5 / 9, offset=-17.7777777778,
        )],
    ))
    overview = workspaces.create_workspace(ExperimentCreateRequest(
        name="清洗对齐测试", objective="验证单位换算和时间对齐", batchCode=None,
        targetProduct="培养产物", targetMetrics=["temperature_c"],
        adapterPack={"enterpriseKey": "enterprise-a", "deviceType": "reactor-x", "packVersion": "1.0.0"},
    ), {
        "enterpriseKey": pack.enterpriseKey, "deviceType": pack.deviceType,
        "packVersion": pack.packVersion, "packId": pack.packId, "contentHash": pack.contentHash,
    })
    asset = files.save_text_file(overview.experimentId, ExperimentTextFileUploadRequest(
        fileName="reactor.csv", content=content,
    ))
    intake = DataCollectionLocalizationAgent(files, workspaces, packs, store)
    intake.create_run(overview.experimentId, asset.assetId)
    intake.confirm(overview.experimentId, ExperimentConfirmFieldMappingsRequest(mappings=[
        ExperimentConfirmedFieldMapping(
            assetId=asset.assetId, originalColumn="time", standardField="timestamp",
            displayName="时间", unit=None, confirmedBy="owner",
        ),
        ExperimentConfirmedFieldMapping(
            assetId=asset.assetId, originalColumn="TempF", standardField="temperature_c",
            displayName="温度", unit="C", confirmedBy="owner",
        ),
    ]))
    return store, files, workspaces, intake, overview, asset


def test_cleaning_run_executes_unit_conversion_and_normalizes_timestamps(tmp_path) -> None:
    store, files, workspaces, intake, overview, _ = setup_pipeline(
        tmp_path,
        "time,TempF\n2026-07-21 08:00:00,98.6\n2026-07-21 08:00:10,100.4",
    )
    agent = CleaningAlignmentAgent(files, workspaces, intake, store)

    run = agent.create_run(overview.experimentId, CleaningAlignmentConfig())

    assert run.status == "completed"
    assert run.alignedRowCount == 2
    assert run.alignedRows[0]["temperature_c"] == pytest.approx(37.0, abs=1e-5)
    assert run.alignedRows[1]["temperature_c"] == pytest.approx(38.0, abs=1e-5)
    assert run.alignedRows[0]["timestamp"].endswith("+00:00")
    formula = next(item for item in run.conversionEvidence if item.originalColumn == "TempF")
    assert formula.scale == pytest.approx(5 / 9)
    assert formula.sourceUnit == "F" and formula.targetUnit == "C"
    assert run.inputFingerprint.startswith("sha256:")
    assert run.outputHash.startswith("sha256:")


def test_cleaning_accepts_dotnet_seven_digit_fractional_seconds(tmp_path) -> None:
    store, files, workspaces, intake, overview, _ = setup_pipeline(
        tmp_path,
        "time,TempF\n2026-07-21T08:00:00.0000000+00:00,98.6",
    )
    agent = CleaningAlignmentAgent(files, workspaces, intake, store)

    run = agent.create_run(overview.experimentId, CleaningAlignmentConfig())

    assert run.status == "completed"
    assert run.quality.invalidTimestampCount == 0
    assert run.alignedRows[0]["timestamp"] == "2026-07-21T08:00:00+00:00"


def test_quality_issues_require_human_review_and_current_input(tmp_path) -> None:
    store, files, workspaces, intake, overview, _ = setup_pipeline(
        tmp_path,
        "time,TempF\n2026-07-21 08:00:00,bad\n2026-07-21 08:00:00,98.6",
    )
    agent = CleaningAlignmentAgent(files, workspaces, intake, store)
    run = agent.create_run(overview.experimentId, CleaningAlignmentConfig())
    assert run.status == "needsReview"
    assert run.quality.invalidNumericCount == 1
    assert run.quality.duplicateTimestampCount == 1
    with pytest.raises(ValueError, match="quality review"):
        agent.assert_snapshot_ready(overview.experimentId)
    confirmed = agent.confirm_review(
        overview.experimentId, run.runId, "quality-owner", "保留异常记录用于复盘",
    )
    assert confirmed.status == "confirmed"
    agent.assert_snapshot_ready(overview.experimentId)

    files.save_text_file(overview.experimentId, ExperimentTextFileUploadRequest(
        fileName="extra.csv", content="time,TempF\n2026-07-21 08:00:20,101.0",
    ))
    with pytest.raises(ValueError, match="input fingerprint"):
        agent.assert_snapshot_ready(overview.experimentId)


def test_cleaning_run_and_review_recover_after_restart(tmp_path) -> None:
    store, files, workspaces, intake, overview, _ = setup_pipeline(
        tmp_path,
        "time,TempF\n2026-07-21 08:00:00,bad",
    )
    agent1 = CleaningAlignmentAgent(files, workspaces, intake, store)
    run = agent1.create_run(overview.experimentId, CleaningAlignmentConfig())
    agent1.confirm_review(overview.experimentId, run.runId, "owner", "已核对原始设备记录")

    store2 = SqliteExperimentDataStore(tmp_path / "data.db", tmp_path / "objects")
    files2 = ExperimentFileService(store2)
    intake2 = DataCollectionLocalizationAgent(
        files2, workspaces,
        DeviceAdapterPackService(SqliteDeviceAdapterPackStore(tmp_path / "packs.db")),
        store2,
    )
    agent2 = CleaningAlignmentAgent(files2, workspaces, intake2, store2)
    recovered = agent2.latest_run(overview.experimentId)
    assert recovered.runId == run.runId
    assert recovered.status == "confirmed"
    assert recovered.reviewedBy == "owner"


def test_cleaning_api_binds_dataset_snapshot_lineage(monkeypatch, tmp_path) -> None:
    store, files, workspaces, intake, overview, _ = setup_pipeline(
        tmp_path,
        "time,TempF\n2026-07-21 08:00:00,98.6\n2026-07-21 08:00:10,100.4",
    )
    cleaning = CleaningAlignmentAgent(files, workspaces, intake, store)
    monkeypatch.setattr(experiments_router, "experiment_file_service", files)
    monkeypatch.setattr(experiments_router, "experiment_service", workspaces)
    monkeypatch.setattr(experiments_router, "data_collection_localization_agent", intake)
    monkeypatch.setattr(experiments_router, "cleaning_alignment_agent", cleaning)

    created = client.post(
        f"/experiments/{overview.experimentId}/cleaning-alignment-runs",
        json={},
    )
    assert created.status_code == 200
    run = created.json()
    snapshot = client.post(f"/experiments/{overview.experimentId}/dataset-snapshots")
    assert snapshot.status_code == 200
    assert snapshot.json()["cleaningRunId"] == run["runId"]
    assert snapshot.json()["cleaningOutputHash"] == run["outputHash"]
    assert snapshot.json()["alignedRows"][0]["temperature_c"] == pytest.approx(37.0)
