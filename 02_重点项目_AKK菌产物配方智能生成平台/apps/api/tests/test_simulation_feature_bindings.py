import pytest

from app.model_registry.bindings import (
    FeatureBindingEntry, FeatureBindingVersion, SimulationFeatureBindingService,
    SqliteFeatureBindingStore,
)
from app.feature_binding_advisor.contracts import DeviceAdapterPackReference
from app.schemas.simulation import SimulationPredictRequest
from app.services.simulation_service import SimulationService


def binding(version: str = "binding-v1") -> FeatureBindingVersion:
    return FeatureBindingVersion(
        bindingVersion=version, experimentId="exp-real", modelVersion="model-v1",
        featureNames=["temperature_c", "ph", "agitation_rpm"],
        entries=[
            FeatureBindingEntry(modelFeature="temperature_c", standardField="temperature_c", simulationParameter="temperatureC", sourceUnit="℃", targetUnit="℃"),
            FeatureBindingEntry(modelFeature="ph", standardField="ph", simulationParameter="ph", sourceUnit="pH", targetUnit="pH"),
            FeatureBindingEntry(modelFeature="agitation_rpm", standardField="agitation_rpm", simulationParameter="stirringRpm", sourceUnit="rpm", targetUnit="rpm", scale=0.5),
        ],
        confirmedBy="研发负责人", confirmationReason="字段和单位已核对", createdAt="2026-07-20T12:00:00+00:00",
    )


def test_confirmed_binding_persists_and_version_reuse_is_lineage_safe(tmp_path) -> None:
    store = SqliteFeatureBindingStore(tmp_path / "bindings.db")
    item = binding(); assert store.save(item) == item
    assert store.latest("exp-real", "model-v1") == item
    assert store.save(item) == item
    with pytest.raises(ValueError, match="different binding"):
        store.save(item.model_copy(update={"confirmedBy": "other"}))


def test_binding_requires_exact_feature_coverage_and_supported_parameters() -> None:
    payload = binding().model_dump()
    payload["entries"] = payload["entries"][:2]
    with pytest.raises(ValueError, match="exactly cover"):
        FeatureBindingVersion.model_validate(payload)
    payload = binding().model_dump(); payload["entries"][2] = payload["entries"][0]
    with pytest.raises(ValueError, match="exactly cover"):
        FeatureBindingVersion.model_validate(payload)
    payload = binding().model_dump(); payload["entries"][0]["simulationParameter"] = "unknownKnob"
    with pytest.raises(ValueError, match="unsupported simulation parameter"):
        FeatureBindingVersion.model_validate(payload)


def test_binding_converts_parameters_and_emits_audit_values(tmp_path) -> None:
    service = SimulationFeatureBindingService(SqliteFeatureBindingStore(tmp_path / "bindings.db"))
    service.confirm(binding())
    result = service.bind("exp-real", "model-v1", {"temperatureC": 37, "ph": 6.8, "stirringRpm": 200})
    assert result.modelInputs == {"temperature_c": 37.0, "ph": 6.8, "agitation_rpm": 100.0}
    assert result.bindingVersion == "binding-v1"
    rpm = next(item for item in result.audit if item.modelFeature == "agitation_rpm")
    assert rpm.sourceValue == 200 and rpm.modelValue == 100
    with pytest.raises(ValueError, match="missing simulation parameter"):
        service.bind("exp-real", "model-v1", {"temperatureC": 37, "ph": 6.8})


def test_binding_persists_suggestion_and_adapter_pack_lineage(tmp_path) -> None:
    reference = DeviceAdapterPackReference(
        packId="adapter-enterprise-a-reactor-1.0.0", enterpriseKey="enterprise-a",
        deviceType="reactor", packVersion="1.0.0", contentHash="sha256:" + "a" * 64,
    )
    item = binding().model_copy(update={
        "suggestionRunId": "binding-suggestion-1",
        "adapterPack": reference,
    })
    service = SimulationFeatureBindingService(
        SqliteFeatureBindingStore(tmp_path / "lineage-bindings.db"),
    )

    saved = service.confirm(item)
    result = service.bind(
        "exp-real", "model-v1",
        {"temperatureC": 37, "ph": 6.8, "stirringRpm": 200},
    )

    assert saved.suggestionRunId == "binding-suggestion-1"
    assert saved.adapterPack == reference
    assert result.suggestionRunId == "binding-suggestion-1"
    assert result.adapterPack == reference


def test_parameter_dictionary_custom_key_can_be_bound_and_audited(tmp_path) -> None:
    base = binding()
    item = base.model_copy(update={
        "featureNames": ["temperature_c", "custom_viscosity", "agitation_rpm"],
        "entries": [
            base.entries[0],
            FeatureBindingEntry(modelFeature="custom_viscosity", standardField="viscosity", simulationParameter="custom_1", sourceUnit="mPa·s", targetUnit="mPa·s"),
            base.entries[2],
        ],
        "bindingVersion": "binding-custom-v1",
    })
    service = SimulationFeatureBindingService(SqliteFeatureBindingStore(tmp_path / "custom.db"))
    service.confirm(item)

    result = service.bind("exp-real", "model-v1", {"temperatureC": 37, "custom_1": 18.5, "stirringRpm": 200})

    assert result.modelInputs["custom_viscosity"] == 18.5


def test_simulation_request_accepts_only_controlled_custom_parameter_keys() -> None:
    base = {
        "targetProduct": "示例产物", "productFormat": "culture-medium", "carbonSource": "BFP",
        "carbonConcentration": 1.0, "cultureHours": 48, "temperatureC": 37.0, "ph": 6.8,
        "anaerobicScore": 0.9, "pressureMpa": 40, "stirringRpm": 120, "pretreated": False,
        "customParameters": {"custom_1": 18.5},
    }
    request = SimulationPredictRequest.model_validate(base)
    assert request.customParameters == {"custom_1": 18.5}
    with pytest.raises(ValueError, match="invalid custom parameter key"):
        SimulationPredictRequest.model_validate({**base, "customParameters": {"startMotor": 1}})


def test_rule_prediction_echoes_custom_parameters_and_marks_calculation_boundary() -> None:
    request = SimulationPredictRequest.model_validate({
        "targetProduct": "示例产物", "productFormat": "culture-medium", "carbonSource": "BFP",
        "carbonConcentration": 1.0, "cultureHours": 48, "temperatureC": 37.0, "ph": 6.8,
        "anaerobicScore": 0.9, "pressureMpa": 40, "stirringRpm": 120, "pretreated": False,
        "customParameters": {"custom_1": 18.5},
    })

    response = SimulationService().predict(request)

    assert response.customParameters == {"custom_1": 18.5}
    assert any("尚未将其纳入评分" in risk for risk in response.risks)
