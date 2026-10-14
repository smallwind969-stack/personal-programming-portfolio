import base64

import pytest
from fastapi.testclient import TestClient

from app.feature_binding_advisor.adapter_pack import DeviceAdapterPackService, SqliteDeviceAdapterPackStore
from app.repositories.sqlite_repository import SqliteRepository
from app.schemas.experiments import (
    ExperimentConfirmFieldMappingsRequest,
    ExperimentConfirmedFieldMapping,
    ExperimentCreateRequest,
    ExperimentTextFileUploadRequest,
)
from app.services.data_collection_localization_agent import DataCollectionLocalizationAgent
from app.services.experiment_data_store import SqliteExperimentDataStore
from app.services.experiment_file_service import ExperimentFileService
from app.services.experiment_service import ExperimentService
from app.main import app
from app.routers import experiments as experiments_router

client = TestClient(app)


def mapping(asset_id: str) -> ExperimentConfirmFieldMappingsRequest:
    return ExperimentConfirmFieldMappingsRequest(mappings=[
        ExperimentConfirmedFieldMapping(
            assetId=asset_id, originalColumn="time", standardField="timestamp",
            displayName="时间", unit=None, confirmedBy="owner",
        ),
        ExperimentConfirmedFieldMapping(
            assetId=asset_id, originalColumn="Temp", standardField="temperature_c",
            displayName="温度", unit="C", confirmedBy="owner",
        ),
    ])


def test_file_assets_audits_mappings_and_snapshots_recover_after_restart(tmp_path) -> None:
    store1 = SqliteExperimentDataStore(tmp_path / "data.db", tmp_path / "objects")
    service1 = ExperimentFileService(store1)
    asset = service1.save_text_file("exp-persist", ExperimentTextFileUploadRequest(
        fileName="reactor.csv", content="time,Temp\n2026-01-01 00:00:00,36.5\n2026-01-01 00:00:10,36.7",
    ))
    service1.confirm_field_mappings("exp-persist", mapping(asset.assetId))
    snapshot = service1.create_dataset_snapshot("exp-persist")

    service2 = ExperimentFileService(SqliteExperimentDataStore(tmp_path / "data.db", tmp_path / "objects"))

    assert service2.list_file_assets("exp-persist")[0].contentHash == asset.contentHash
    assert service2.list_audit_events("exp-persist").eventCount == 1
    assert service2.get_confirmed_field_mappings("exp-persist").mappingCount == 2
    assert service2.get_latest_dataset_snapshot("exp-persist").snapshotId == snapshot.snapshotId
    assert service2.verify_asset_integrity(asset.assetId) is True


def test_dataset_snapshot_uses_only_parsed_assets_and_retains_source_evidence(tmp_path) -> None:
    service = ExperimentFileService(SqliteExperimentDataStore(tmp_path / "data.db", tmp_path / "objects"))
    raw = service.save_text_file("exp-lineage-snapshot", ExperimentTextFileUploadRequest(
        fileName="reactor.raw", content=base64.b64encode(b"DEVICE-RAW").decode("ascii"), encoding="base64",
    ))
    converted = service.save_text_file("exp-lineage-snapshot", ExperimentTextFileUploadRequest(
        fileName="reactor.csv", content="time,Temp\n2026-01-01T00:00:00,36.5\n",
        sourceAssetId=raw.assetId,
    ))
    service.confirm_field_mappings("exp-lineage-snapshot", mapping(converted.assetId))

    snapshot = service.create_dataset_snapshot("exp-lineage-snapshot")

    assert snapshot.assetCount == 1
    assert snapshot.evidenceAssetCount == 1
    assert snapshot.analysisAssetIds == [converted.assetId]
    assert snapshot.sourceEvidenceAssetIds == [raw.assetId]


def test_content_addressed_asset_detects_tampering_and_soft_delete_is_audited(tmp_path) -> None:
    store = SqliteExperimentDataStore(tmp_path / "data.db", tmp_path / "objects")
    service = ExperimentFileService(store)
    asset = service.save_text_file("exp-integrity", ExperimentTextFileUploadRequest(
        fileName="device.csv", content="Temp\n36.5",
    ))
    object_path = store.object_path(asset.contentHash)
    object_path.write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="integrity"):
        service.verify_asset_integrity(asset.assetId)

    service.delete_file_asset("exp-integrity", asset.assetId, "owner", "错误上传")
    assert service.list_file_assets("exp-integrity") == []
    timeline = service.list_audit_events("exp-integrity")
    assert timeline.events[-1].action == "delete_file"
    assert timeline.events[-1].operator == "owner"
    assert timeline.events[-1].reason == "错误上传"
    assert object_path.exists()


def test_data_intake_runs_recover_with_confirmation_state(tmp_path) -> None:
    store = SqliteExperimentDataStore(tmp_path / "data.db", tmp_path / "objects")
    files1 = ExperimentFileService(store)
    workspaces = ExperimentService(SqliteRepository(tmp_path / "platform.db"))
    overview = workspaces.create_workspace(ExperimentCreateRequest(
        name="恢复测试", objective="恢复接入运行", batchCode=None,
        targetProduct="产物", targetMetrics=["OD600"], adapterPack=None,
    ), None)
    packs = DeviceAdapterPackService(SqliteDeviceAdapterPackStore(tmp_path / "packs.db"))
    asset = files1.save_text_file(overview.experimentId, ExperimentTextFileUploadRequest(
        fileName="device.csv", content="time,Temp\n2026-01-01,36.5",
    ))
    agent1 = DataCollectionLocalizationAgent(files1, workspaces, packs, store)
    run = agent1.create_run(overview.experimentId, asset.assetId)

    files2 = ExperimentFileService(SqliteExperimentDataStore(tmp_path / "data.db", tmp_path / "objects"))
    agent2 = DataCollectionLocalizationAgent(files2, workspaces, packs, files2.store)
    assert agent2.latest_run(overview.experimentId).runId == run.runId
    agent2.confirm(overview.experimentId, mapping(asset.assetId))

    files3 = ExperimentFileService(SqliteExperimentDataStore(tmp_path / "data.db", tmp_path / "objects"))
    agent3 = DataCollectionLocalizationAgent(files3, workspaces, packs, files3.store)
    recovered = agent3.latest_run(overview.experimentId)
    assert recovered.status == "confirmed"
    assert [item.standardField for item in recovered.transformations] == ["timestamp", "temperature_c"]


def test_asset_integrity_and_soft_delete_api(monkeypatch, tmp_path) -> None:
    store = SqliteExperimentDataStore(tmp_path / "data.db", tmp_path / "objects")
    service = ExperimentFileService(store)
    asset = service.save_text_file("exp-api-asset", ExperimentTextFileUploadRequest(
        fileName="device.csv", content="Temp\n36.5",
    ))
    monkeypatch.setattr(experiments_router, "experiment_file_service", service)

    verified = client.get(f"/experiments/exp-api-asset/files/{asset.assetId}/integrity")
    assert verified.status_code == 200
    assert verified.json()["verified"] is True
    assert verified.json()["storageScheme"] == "content-addressed-sha256"

    deleted = client.request(
        "DELETE", f"/experiments/exp-api-asset/files/{asset.assetId}",
        json={"operator": "owner", "reason": "重复采集错误"},
    )
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    assert client.get(f"/experiments/exp-api-asset/files/{asset.assetId}/integrity").status_code == 404


def test_dataset_snapshot_requires_live_assets_and_confirmed_mappings(tmp_path) -> None:
    service = ExperimentFileService(SqliteExperimentDataStore(tmp_path / "data.db", tmp_path / "objects"))
    with pytest.raises(ValueError, match="file asset"):
        service.create_dataset_snapshot("exp-empty")
    asset = service.save_text_file("exp-empty", ExperimentTextFileUploadRequest(
        fileName="device.csv", content="Temp\n36.5",
    ))
    with pytest.raises(ValueError, match="field mapping"):
        service.create_dataset_snapshot("exp-empty")
    service.confirm_field_mappings("exp-empty", ExperimentConfirmFieldMappingsRequest(mappings=[
        ExperimentConfirmedFieldMapping(
            assetId=asset.assetId, originalColumn="Temp", standardField="temperature_c",
            displayName="温度", unit="C", confirmedBy="owner",
        ),
    ]))
    service.delete_file_asset("exp-empty", asset.assetId, "owner", "撤销错误文件")
    with pytest.raises(ValueError, match="file asset"):
        service.create_dataset_snapshot("exp-empty")

def test_content_store_preserves_crlf_bytes_for_integrity_verification(tmp_path):
    store = SqliteExperimentDataStore(tmp_path / "runs.db", tmp_path / "objects")
    content = "timestamp,value\r\n2026-07-21T00:00:00Z,1.0\r\n"
    content_hash = sha256(content.encode("utf-8")).hexdigest()

    store.put_content(content, content_hash)

    assert store.read_verified(content_hash) == content
from hashlib import sha256
