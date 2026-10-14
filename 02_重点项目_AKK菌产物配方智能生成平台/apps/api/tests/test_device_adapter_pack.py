import pytest

from app.feature_binding_advisor.adapter_pack import (
    DeviceAdapterEntry, DeviceAdapterPackCreate, DeviceAdapterPackService, SqliteDeviceAdapterPackStore,
)


def request() -> DeviceAdapterPackCreate:
    return DeviceAdapterPackCreate(
        enterpriseKey="enterprise-a", deviceType="bioreactor-x", packVersion="1.0.0",
        entries=[
            DeviceAdapterEntry(sourceFieldAlias="Temp", standardField="temperature_c", simulationParameter="temperatureC", sourceUnit="°C", targetUnit="℃"),
            DeviceAdapterEntry(sourceFieldAlias="rpm", standardField="agitation_rpm", simulationParameter="stirringRpm", sourceUnit="rpm", targetUnit="rpm"),
        ], createdBy="integration-owner",
    )


def test_adapter_pack_export_import_round_trip_and_persistence(tmp_path) -> None:
    service = DeviceAdapterPackService(SqliteDeviceAdapterPackStore(tmp_path / "packs.db"))
    exported = service.export(request())
    assert exported.contentHash.startswith("sha256:") and exported.integrityScheme == "canonical-json-sha256"
    imported = service.import_pack(exported.model_dump(mode="json"))
    assert imported == exported
    assert service.store.get("enterprise-a", "bioreactor-x", "1.0.0") == exported


def test_adapter_pack_rejects_tamper_unknown_parameter_and_version_reuse(tmp_path) -> None:
    service = DeviceAdapterPackService(SqliteDeviceAdapterPackStore(tmp_path / "packs.db"))
    exported = service.export(request())
    tampered = exported.model_dump(mode="json"); tampered["entries"][0]["scale"] = 2
    with pytest.raises(ValueError, match="integrity"):
        service.import_pack(tampered)
    invalid = request().model_dump(); invalid["entries"][0]["simulationParameter"] = "startMotor"
    with pytest.raises(ValueError, match="unsupported simulation parameter"):
        DeviceAdapterPackCreate.model_validate(invalid)
    changed = request().model_copy(deep=True); changed.entries[0].offset = 1
    with pytest.raises(ValueError, match="different content"):
        service.export(changed)


def test_adapter_pack_comparison_reports_added_removed_changed_and_unchanged(tmp_path) -> None:
    service = DeviceAdapterPackService(SqliteDeviceAdapterPackStore(tmp_path / "packs.db"))
    service.export(request())
    target = DeviceAdapterPackCreate(
        enterpriseKey="enterprise-a", deviceType="bioreactor-x", packVersion="2.0.0",
        createdBy="integration-owner", entries=[
            DeviceAdapterEntry(
                sourceFieldAlias="Temp", standardField="temperature_c",
                simulationParameter="temperatureC", sourceUnit=request().entries[0].sourceUnit, targetUnit="K",
                scale=1.0, offset=273.15,
            ),
            DeviceAdapterEntry(
                sourceFieldAlias="pH_Value", standardField="ph",
                simulationParameter="ph", sourceUnit="pH", targetUnit="pH",
            ),
        ],
    )
    service.export(target)

    comparison = service.compare("enterprise-a", "bioreactor-x", "1.0.0", "2.0.0")

    assert [item.sourceFieldAlias for item in comparison.added] == ["pH_Value"]
    assert [item.sourceFieldAlias for item in comparison.removed] == ["rpm"]
    assert [item.sourceFieldAlias for item in comparison.changed] == ["Temp"]
    assert comparison.changed[0].changedFields == ["targetUnit", "offset"]
    assert comparison.unchangedCount == 0
    assert comparison.baseContentHash.startswith("sha256:")
    assert comparison.targetContentHash.startswith("sha256:")


def test_adapter_pack_comparison_rejects_same_version_and_missing_pack(tmp_path) -> None:
    service = DeviceAdapterPackService(SqliteDeviceAdapterPackStore(tmp_path / "packs.db"))
    service.export(request())
    with pytest.raises(ValueError, match="different versions"):
        service.compare("enterprise-a", "bioreactor-x", "1.0.0", "1.0.0")
    with pytest.raises(LookupError, match="not found"):
        service.compare("enterprise-a", "bioreactor-x", "1.0.0", "9.0.0")
