from app.repositories.sqlite_repository import SqliteRepository
from app.schemas.experiments import ExperimentCreateRequest
from app.services.experiment_service import ExperimentService
from app.feature_binding_advisor.adapter_pack import (
    DeviceAdapterEntry, DeviceAdapterPackCreate, DeviceAdapterPackService, SqliteDeviceAdapterPackStore,
)
from app.main import app
from app.routers import experiments as experiments_router
from fastapi.testclient import TestClient

client = TestClient(app)


def request() -> ExperimentCreateRequest:
    return ExperimentCreateRequest(
        name="首次发酵建模实验",
        objective="建立温度与菌体活性的映射关系",
        batchCode="B-001",
        targetProduct="AKK 发酵产物",
        targetMetrics=["OD600", "活菌率"],
        adapterPack={
            "enterpriseKey": "enterprise-a",
            "deviceType": "bioreactor-x",
            "packVersion": "1.0.0",
        },
    )


def test_workspace_create_persists_adapter_lineage_and_waiting_state(tmp_path) -> None:
    repository = SqliteRepository(tmp_path / "platform.db")
    service = ExperimentService(repository)
    reference = {
        "enterpriseKey": "enterprise-a", "deviceType": "bioreactor-x",
        "packVersion": "1.0.0", "packId": "adapter-enterprise-a-bioreactor-x-1.0.0",
        "contentHash": "sha256:" + "a" * 64,
    }

    created = service.create_workspace(request(), reference)
    reloaded = ExperimentService(SqliteRepository(tmp_path / "platform.db")).get_workspace_overview(created.experimentId)

    assert reloaded is not None
    assert reloaded.adapterPack is not None
    assert reloaded.adapterPack.contentHash == reference["contentHash"]
    assert reloaded.targetProduct == "AKK 发酵产物"
    assert reloaded.targetMetrics == ["OD600", "活菌率"]
    assert reloaded.stages[0].status == "needsReview"
    assert reloaded.stages[1].canRun is False
    assert "待上传" in reloaded.resultSummary


def test_workspace_create_persists_universal_production_context(tmp_path) -> None:
    repository = SqliteRepository(tmp_path / "platform.db")
    service = ExperimentService(repository)
    created = service.create_workspace(request().model_copy(update={
        "adapterPack": None,
        "productionContext": {
            "industry": "精细化工",
            "processType": "连续混配",
            "lineName": "试验线 C-02",
            "materialSystem": "水性功能材料",
            "criticalParameters": ["进料流量", "釜温", "黏度"],
        },
    }), None)

    reloaded = ExperimentService(SqliteRepository(tmp_path / "platform.db")).get_workspace_overview(created.experimentId)

    assert reloaded is not None
    assert reloaded.productionContext.industry == "精细化工"
    assert reloaded.productionContext.processType == "连续混配"
    assert reloaded.productionContext.criticalParameters == ["进料流量", "釜温", "黏度"]


def test_historical_workspace_receives_neutral_production_context_default(tmp_path) -> None:
    service = ExperimentService(SqliteRepository(tmp_path / "platform.db"))

    historical = service.get_workspace_overview("exp-akk-018")

    assert historical is not None
    assert historical.productionContext.industry == "未配置"
    assert historical.productionContext.criticalParameters == []


def test_legacy_sample_workspace_receives_sample_context_without_rewriting_record(tmp_path) -> None:
    repository = SqliteRepository(tmp_path / "platform.db")
    service = ExperimentService(repository)
    created = service.create_workspace(
        request().model_copy(update={"adapterPack": None}), None, source_type="sample",
    )
    raw = repository.get_experiment_workspace(created.experimentId)
    assert raw is not None
    raw.pop("productionContext", None)
    repository.update_experiment_workspace(raw)

    reloaded = service.get_workspace_overview(created.experimentId)

    assert reloaded is not None
    assert reloaded.productionContext.industry == "生物制造与功能食品"
    assert "溶氧" in reloaded.productionContext.criticalParameters


def test_workspace_archive_includes_persisted_workspace_without_overwriting_demo(tmp_path) -> None:
    service = ExperimentService(SqliteRepository(tmp_path / "platform.db"))
    created = service.create_workspace(request().model_copy(update={"adapterPack": None}), None)

    archive = service.list_workspace_archive()

    assert archive.totalCount >= 5
    assert archive.experiments[0].experimentId == created.experimentId
    assert any(item.experimentId == "exp-akk-018" for item in archive.experiments)


def test_workspace_source_lineage_persists_and_historical_records_default_to_enterprise(tmp_path) -> None:
    repository = SqliteRepository(tmp_path / "platform.db")
    service = ExperimentService(repository)

    blank = service.create_workspace(
        request().model_copy(update={"adapterPack": None, "sourceType": "blank"}),
        None,
    )
    reloaded = ExperimentService(repository).get_workspace_overview(blank.experimentId)

    assert reloaded is not None
    assert reloaded.sourceType == "blank"
    assert reloaded.sampleTemplateVersion is None
    historical = service.get_workspace_overview("exp-akk-018")
    assert historical is not None
    assert historical.sourceType == "enterprise"


def test_workspace_create_api_revalidates_and_locks_adapter_pack(monkeypatch, tmp_path) -> None:
    packs = DeviceAdapterPackService(SqliteDeviceAdapterPackStore(tmp_path / "packs.db"))
    pack = packs.export(DeviceAdapterPackCreate(
        enterpriseKey="enterprise-a", deviceType="bioreactor-x", packVersion="1.0.0",
        createdBy="owner", entries=[DeviceAdapterEntry(
            sourceFieldAlias="Temp", standardField="temperature_c",
            simulationParameter="temperatureC", sourceUnit="C", targetUnit="C",
        )],
    ))
    workspaces = ExperimentService(SqliteRepository(tmp_path / "platform.db"))
    monkeypatch.setattr(experiments_router, "experiment_service", workspaces)
    monkeypatch.setattr(experiments_router, "device_adapter_pack_service", packs)

    response = client.post("/experiments/workspaces", json=request().model_dump(mode="json"))

    assert response.status_code == 200
    assert response.json()["adapterPack"] == {
        "enterpriseKey": pack.enterpriseKey, "deviceType": pack.deviceType,
        "packVersion": pack.packVersion, "packId": pack.packId, "contentHash": pack.contentHash,
    }
    missing = request().model_copy(deep=True)
    missing.adapterPack.packVersion = "9.0.0"
    assert client.post("/experiments/workspaces", json=missing.model_dump(mode="json")).status_code == 404
