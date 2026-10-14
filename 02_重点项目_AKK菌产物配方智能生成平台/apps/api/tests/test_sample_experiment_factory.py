import pytest

from app.feature_binding_advisor.adapter_pack import DeviceAdapterPackService, SqliteDeviceAdapterPackStore
from app.repositories.sqlite_repository import SqliteRepository
from app.sample_experiments.contracts import SampleExperimentCreate
from app.sample_experiments.service import SampleExperimentService
from app.services.data_collection_localization_agent import DataCollectionLocalizationAgent
from app.services.experiment_file_service import ExperimentFileService
from app.services.experiment_service import ExperimentService


def build_service(tmp_path) -> SampleExperimentService:
    workspace_service = ExperimentService(SqliteRepository(tmp_path / "platform.db"))
    file_service = ExperimentFileService()
    adapter_service = DeviceAdapterPackService(SqliteDeviceAdapterPackStore(tmp_path / "packs.db"))
    intake_agent = DataCollectionLocalizationAgent(file_service, workspace_service, adapter_service)
    return SampleExperimentService(workspace_service, file_service, intake_agent)


def test_factory_creates_isolated_versioned_sample_with_ingestion_evidence(tmp_path) -> None:
    service = build_service(tmp_path)

    result = service.create(SampleExperimentCreate(templateKey="algae-culture"))

    assert result.overview.experimentId.startswith("exp-")
    assert result.overview.sourceType == "sample"
    assert result.overview.sampleTemplateVersion == "algae-culture-v1"
    assert result.templateKey == "algae-culture"
    assert result.templateVersion == "algae-culture-v1"
    assert result.asset.originalName == "algae-culture-v1.csv"
    assert result.asset.rowCount >= 36
    assert result.asset.columnNames == [
        "timestamp", "temperature_c", "ph", "agitation_rpm",
        "dissolved_oxygen_pct", "od600",
    ]
    assert result.asset.contentHash == result.templateContentHash
    assert result.intakeRunId.startswith("intake-")
    assert service.fileService.verify_asset_integrity(result.asset.assetId)


def test_factory_creates_independent_instances_and_rejects_unknown_template(tmp_path) -> None:
    service = build_service(tmp_path)

    first = service.create(SampleExperimentCreate(templateKey="algae-culture"))
    second = service.create(SampleExperimentCreate(templateKey="algae-culture"))

    assert first.overview.experimentId != second.overview.experimentId
    assert first.templateContentHash == second.templateContentHash

    try:
        SampleExperimentCreate(templateKey="unknown")
    except ValueError as exc:
        assert "templateKey" in str(exc)
    else:
        raise AssertionError("unknown sample template must be rejected")


def test_factory_rolls_back_workspace_and_asset_when_intake_fails(tmp_path, monkeypatch) -> None:
    service = build_service(tmp_path)
    captured = {}
    original_save = service.fileService.save_text_file

    def capture_asset(experiment_id, request):
        asset = original_save(experiment_id, request)
        captured.update(experimentId=experiment_id, assetId=asset.assetId)
        return asset

    monkeypatch.setattr(service.fileService, "save_text_file", capture_asset)
    monkeypatch.setattr(
        service.intakeAgent,
        "create_run",
        lambda *_: (_ for _ in ()).throw(RuntimeError("injected intake failure")),
    )
    before = service.workspaceService.list_workspace_archive().totalCount

    with pytest.raises(RuntimeError, match="injected intake failure"):
        service.create(SampleExperimentCreate(templateKey="algae-culture"))

    assert service.workspaceService.list_workspace_archive().totalCount == before
    assert service.workspaceService.get_workspace_overview(captured["experimentId"]) is None
    assert service.fileService.get_file_asset(captured["experimentId"], captured["assetId"]) is None
