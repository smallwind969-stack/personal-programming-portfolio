import pytest
from fastapi.testclient import TestClient

from app.feature_binding_advisor.adapter_pack import (
    DeviceAdapterEntry, DeviceAdapterPackCreate, DeviceAdapterPackService, SqliteDeviceAdapterPackStore,
)
from app.repositories.sqlite_repository import SqliteRepository
from app.schemas.experiments import (
    ExperimentConfirmFieldMappingsRequest, ExperimentConfirmedFieldMapping,
    ExperimentCreateRequest, ExperimentTextFileUploadRequest,
)
from app.services.data_collection_localization_agent import DataCollectionLocalizationAgent
from app.services.experiment_file_service import ExperimentFileService
from app.services.experiment_service import ExperimentService
from app.services.cleaning_alignment_agent import CleaningAlignmentAgent
from app.schemas.experiments import CleaningAlignmentConfig
from app.main import app
from app.routers import experiments as experiments_router

client = TestClient(app)


def build_agent(tmp_path):
    files = ExperimentFileService()
    workspaces = ExperimentService(SqliteRepository(tmp_path / "platform.db"))
    packs = DeviceAdapterPackService(SqliteDeviceAdapterPackStore(tmp_path / "packs.db"))
    pack = packs.export(DeviceAdapterPackCreate(
        enterpriseKey="e-a", deviceType="reactor-x", packVersion="1.0.0", createdBy="owner",
        entries=[
            DeviceAdapterEntry(
                sourceFieldAlias="Temp", standardField="temperature_c",
                simulationParameter="temperatureC", sourceUnit="F", targetUnit="C",
                scale=0.555556, offset=-17.7778,
            ),
            DeviceAdapterEntry(
                sourceFieldAlias="rpm", standardField="agitation_rpm",
                simulationParameter="stirringRpm", sourceUnit="rpm", targetUnit="rpm",
            ),
        ],
    ))
    request = ExperimentCreateRequest(
        name="接入测试实验", objective="验证适配证据", batchCode=None,
        targetProduct="培养产物", targetMetrics=["OD600"],
        adapterPack={"enterpriseKey": "e-a", "deviceType": "reactor-x", "packVersion": "1.0.0"},
    )
    overview = workspaces.create_workspace(request, {
        "enterpriseKey": pack.enterpriseKey, "deviceType": pack.deviceType,
        "packVersion": pack.packVersion, "packId": pack.packId, "contentHash": pack.contentHash,
    })
    return DataCollectionLocalizationAgent(files, workspaces, packs), files, overview


def test_upload_run_applies_locked_adapter_and_emits_conversion_evidence(tmp_path) -> None:
    agent, files, overview = build_agent(tmp_path)
    asset = files.save_text_file(overview.experimentId, ExperimentTextFileUploadRequest(
        fileName="reactor.csv", content="time,Temp,rpm,unknown\n0,98.6,120,7\n1,100.4,140,8",
    ))

    run = agent.create_run(overview.experimentId, asset.assetId)

    assert run.status == "needsReview"
    assert run.adapterPack is not None
    assert run.adapterPack.contentHash == overview.adapterPack.contentHash
    temp = next(item for item in run.transformations if item.originalColumn == "Temp")
    assert temp.standardField == "temperature_c"
    assert temp.simulationParameter == "temperatureC"
    assert temp.scale == pytest.approx(0.555556)
    assert temp.offset == pytest.approx(-17.7778)
    assert temp.sourceUnit == "F" and temp.targetUnit == "C"
    assert any("adapter" in evidence.lower() for evidence in temp.evidence)
    unknown = next(item for item in run.transformations if item.originalColumn == "unknown")
    assert unknown.matched is False and unknown.requiresHumanReview is True


def test_intake_confirmation_gate_requires_all_adapter_matched_fields(tmp_path) -> None:
    agent, files, overview = build_agent(tmp_path)
    asset = files.save_text_file(overview.experimentId, ExperimentTextFileUploadRequest(
        fileName="reactor.csv", content="Temp,rpm\n98.6,120",
    ))
    run = agent.create_run(overview.experimentId, asset.assetId)
    with pytest.raises(ValueError, match="human confirmation"):
        agent.assert_snapshot_ready(overview.experimentId)

    partial = ExperimentConfirmFieldMappingsRequest(mappings=[ExperimentConfirmedFieldMapping(
        assetId=asset.assetId, originalColumn="Temp", standardField="temperature_c",
        displayName="温度", unit="C", confirmedBy="owner",
    )])
    with pytest.raises(ValueError, match="rpm"):
        agent.confirm(overview.experimentId, partial)

    complete = partial.model_copy(deep=True)
    complete.mappings.append(ExperimentConfirmedFieldMapping(
        assetId=asset.assetId, originalColumn="rpm", standardField="agitation_rpm",
        displayName="搅拌速度", unit="rpm", confirmedBy="owner",
    ))
    confirmed = agent.confirm(overview.experimentId, complete)
    assert confirmed.status == "confirmed"
    agent.assert_snapshot_ready(overview.experimentId)


def test_canonical_standard_fields_are_suggested_without_enterprise_adapter(tmp_path) -> None:
    files = ExperimentFileService()
    workspaces = ExperimentService(SqliteRepository(tmp_path / "platform.db"))
    packs = DeviceAdapterPackService(SqliteDeviceAdapterPackStore(tmp_path / "packs.db"))
    overview = workspaces.create_workspace(ExperimentCreateRequest(
        name="标准字段接入测试", objective="验证通用标准字段直接识别",
        targetProduct="菌藻培养产物", targetMetrics=["OD600"], sourceType="blank",
    ), None)
    agent = DataCollectionLocalizationAgent(files, workspaces, packs)
    asset = files.save_text_file(overview.experimentId, ExperimentTextFileUploadRequest(
        fileName="canonical.csv",
        content="timestamp,temperature_c,ph,agitation_rpm,dissolved_oxygen_pct,od600\n2026-01-01T00:00:00Z,37,7.1,180,65,0.2",
    ))

    run = agent.create_run(overview.experimentId, asset.assetId)

    assert run.matchedCount == 6
    by_name = {item.originalColumn: item for item in run.transformations}
    assert by_name["temperature_c"].standardField == "temperature_c"
    assert by_name["temperature_c"].targetUnit == "°C"
    assert by_name["agitation_rpm"].simulationParameter == "stirringRpm"
    assert by_name["od600"].targetUnit == "AU"
    assert all(item.requiresHumanReview for item in run.transformations)
    assert all(any("canonical" in evidence.lower() for evidence in item.evidence) for item in run.transformations)


def test_upload_api_auto_starts_intake_and_blocks_snapshot_until_confirmation(monkeypatch, tmp_path) -> None:
    agent, files, overview = build_agent(tmp_path)
    monkeypatch.setattr(experiments_router, "experiment_file_service", files)
    monkeypatch.setattr(experiments_router, "data_collection_localization_agent", agent)
    monkeypatch.setattr(experiments_router, "experiment_service", agent.workspace_service)
    cleaning = CleaningAlignmentAgent(files, agent.workspace_service, agent)
    monkeypatch.setattr(experiments_router, "cleaning_alignment_agent", cleaning)

    uploaded = client.post(f"/experiments/{overview.experimentId}/files", json={
        "fileName": "reactor.csv", "content": "Temp,rpm\n98.6,120\n100.4,140",
    })
    assert uploaded.status_code == 200
    assert uploaded.json()["adapterApplied"] is True
    assert uploaded.json()["intakeRunId"].startswith("intake-")
    assert agent.workspace_service.get_workspace_overview(overview.experimentId).statusLabel == "字段与单位待确认"
    latest = client.get(f"/experiments/{overview.experimentId}/data-intake-runs/latest")
    assert latest.status_code == 200
    assert latest.json()["matchedCount"] == 2
    assert client.post(f"/experiments/{overview.experimentId}/dataset-snapshots").status_code == 409

    asset_id = uploaded.json()["assetId"]
    confirmed = client.post(f"/experiments/{overview.experimentId}/field-mappings/confirm", json={
        "mappings": [
            {"assetId": asset_id, "originalColumn": "Temp", "standardField": "temperature_c", "displayName": "温度", "unit": "C", "confirmedBy": "owner", "confirmed": True},
            {"assetId": asset_id, "originalColumn": "rpm", "standardField": "agitation_rpm", "displayName": "搅拌速度", "unit": "rpm", "confirmedBy": "owner", "confirmed": True},
        ],
    })
    assert confirmed.status_code == 200
    refreshed = agent.workspace_service.get_workspace_overview(overview.experimentId)
    assert refreshed.status == "running"
    assert refreshed.stages[0].canRun is True
    assert client.get(f"/experiments/{overview.experimentId}/data-intake-runs/latest").json()["status"] == "confirmed"
    cleaning.create_run(overview.experimentId, CleaningAlignmentConfig())
    assert client.post(f"/experiments/{overview.experimentId}/dataset-snapshots").status_code == 200
