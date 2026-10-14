from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.model_registry.contracts import PromotedModelPredictRequest, PromotedModelPrediction, PromotedModelRecord
from app.model_registry.bindings import (
    FeatureBindingConfirmRequest, FeatureBindingVersion,
)
from app.services.experiment_service import experiment_service
from app.model_registry.composite import CompositeModelPrediction, CompositePredictionRequest
from app.research.service import promoted_model_registry
from app.model_registry.runtime import (
    promoted_model_inference_service,
    feature_binding_service,
    composite_prediction_service,
)
from app.feature_binding_advisor.contracts import (
    FeatureBindingSuggestionEnqueueRequest, FeatureBindingSuggestionRun, FeatureBindingSuggestionRunCreate,
)
from app.schemas.agent_commands import AgentCommandTask
from app.agent_queue.sqlite_queue import AgentCommandConflictError
from app.services.agent_command_service import agent_command_service
from app.feature_binding_advisor.adapter_pack import (
    DeviceAdapterPack,
    DeviceAdapterPackComparison,
    DeviceAdapterPackCreate,
)
from app.services.feature_binding_advisor_agent import (
    device_adapter_pack_service, feature_binding_advisor,
)

from app.schemas.simulation import (
    SimulationLlmStatus,
    SimulationPredictRequest,
    SimulationPredictResponse,
    SimulationScenario,
)
from app.services.simulation_service import simulation_service
from app.model_assets.contracts import ModelAssetDetail, ModelAssetSummary
from app.model_assets.runtime import model_asset_center_service

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.get("/model-assets", response_model=list[ModelAssetSummary])
def list_model_assets() -> list[ModelAssetSummary]:
    return model_asset_center_service.list_assets()


@router.get("/model-assets/{experiment_id}/{model_version}", response_model=ModelAssetDetail)
def get_model_asset_detail(experiment_id: str, model_version: str) -> ModelAssetDetail:
    try:
        return model_asset_center_service.get_detail(experiment_id, model_version)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/predict", response_model=SimulationPredictResponse)
def predict_simulation(payload: SimulationPredictRequest) -> SimulationPredictResponse:
    return simulation_service.predict(payload)


@router.post("/experiments/{experiment_id}/promoted-model/predict", response_model=PromotedModelPrediction)
def predict_with_promoted_model(experiment_id: str, payload: PromotedModelPredictRequest) -> PromotedModelPrediction:
    try:
        return promoted_model_inference_service.predict(
            experiment_id, payload.inputs, payload.modelVersion, payload.allowExtrapolation,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/experiments/{experiment_id}/promoted-models", response_model=list[PromotedModelRecord])
def list_promoted_models(experiment_id: str) -> list[PromotedModelRecord]:
    return promoted_model_registry.list(experiment_id)


@router.post("/experiments/{experiment_id}/model-bindings", response_model=FeatureBindingVersion)
def confirm_model_binding(experiment_id: str, payload: FeatureBindingConfirmRequest) -> FeatureBindingVersion:
    _validate_binding_lineage(experiment_id, payload)
    try:
        return feature_binding_service.confirm(FeatureBindingVersion(
            experimentId=experiment_id, createdAt=datetime.now(timezone.utc).isoformat(), **payload.model_dump(),
        ))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _validate_binding_lineage(
    experiment_id: str, payload: FeatureBindingConfirmRequest,
) -> None:
    overview = experiment_service.get_workspace_overview(experiment_id)
    if overview is None:
        if any(entry.simulationParameter.startswith("custom_") for entry in payload.entries):
            raise HTTPException(status_code=404, detail="experiment workspace was not found")
    else:
        allowed = {item.key for item in overview.productionContext.parameterDefinitions}
        allowed.update({"carbonConcentration", "cultureHours", "temperatureC", "ph", "anaerobicScore", "pressureMpa", "stirringRpm"})
        unknown = sorted({entry.simulationParameter for entry in payload.entries} - allowed)
        if unknown:
            raise HTTPException(status_code=422, detail=f"simulation parameters are not registered for this experiment: {', '.join(unknown)}")
    if payload.adapterPack is not None and payload.suggestionRunId is None:
        raise HTTPException(status_code=422, detail="adapter pack lineage requires suggestionRunId")
    if payload.suggestionRunId is None:
        return
    run = feature_binding_advisor.get_run(experiment_id, payload.suggestionRunId)
    if run is None:
        raise HTTPException(status_code=404, detail="binding suggestion run not found")
    if run.modelVersion != payload.modelVersion:
        raise HTTPException(status_code=422, detail="suggestion run model version mismatch")
    expected = run.adapterPack.model_dump(mode="json") if run.adapterPack else None
    supplied = payload.adapterPack.model_dump(mode="json") if payload.adapterPack else None
    if expected != supplied:
        raise HTTPException(status_code=422, detail="adapter pack lineage does not match suggestion run")
    if payload.adapterPack is None:
        return
    reference = payload.adapterPack
    try:
        pack = device_adapter_pack_service.get_verified(
            reference.enterpriseKey, reference.deviceType, reference.packVersion,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if pack is None:
        raise HTTPException(status_code=404, detail="device adapter pack was not found")
    if pack.packId != reference.packId or pack.contentHash != reference.contentHash:
        raise HTTPException(status_code=422, detail="device adapter pack reference failed verification")


@router.post("/experiments/{experiment_id}/composite-predict", response_model=CompositeModelPrediction)
def predict_composite(experiment_id: str, payload: CompositePredictionRequest) -> CompositeModelPrediction:
    try:
        return composite_prediction_service.predict(
            experiment_id, payload.parameters, payload.targetFields, payload.allowExtrapolation,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/experiments/{experiment_id}/models/{model_version}/binding-suggestion-runs", response_model=FeatureBindingSuggestionRun)
def create_binding_suggestion_run(experiment_id: str, model_version: str, payload: FeatureBindingSuggestionRunCreate) -> FeatureBindingSuggestionRun:
    try:
        return feature_binding_advisor.create_run(
            experiment_id, model_version, payload.commandId, payload.adapterPack,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/experiments/{experiment_id}/models/{model_version}/binding-suggestion-runs/enqueue",
    response_model=AgentCommandTask,
)
def enqueue_binding_suggestion_run(
    experiment_id: str, model_version: str, payload: FeatureBindingSuggestionEnqueueRequest,
) -> AgentCommandTask:
    try:
        return agent_command_service.enqueue_binding_suggestion(
            experiment_id, model_version, payload.commandId, payload.priority, payload.adapterPack,
        )
    except AgentCommandConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/experiments/{experiment_id}/binding-suggestion-runs/{run_id}", response_model=FeatureBindingSuggestionRun)
def get_binding_suggestion_run(experiment_id: str, run_id: str) -> FeatureBindingSuggestionRun:
    run = feature_binding_advisor.get_run(experiment_id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="binding suggestion run not found")
    return run


@router.post("/device-adapter-packs/export", response_model=DeviceAdapterPack)
def export_device_adapter_pack(payload: DeviceAdapterPackCreate) -> DeviceAdapterPack:
    try:
        return device_adapter_pack_service.export(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/device-adapter-packs/import", response_model=DeviceAdapterPack)
def import_device_adapter_pack(payload: DeviceAdapterPack) -> DeviceAdapterPack:
    try:
        return device_adapter_pack_service.import_pack(payload.model_dump(mode="json"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/device-adapter-packs", response_model=list[DeviceAdapterPack])
def list_device_adapter_packs(enterpriseKey: str | None = None) -> list[DeviceAdapterPack]:
    return device_adapter_pack_service.store.list(enterpriseKey)


@router.get("/device-adapter-packs/compare", response_model=DeviceAdapterPackComparison)
def compare_device_adapter_packs(
    enterpriseKey: str, deviceType: str, baseVersion: str, targetVersion: str,
) -> DeviceAdapterPackComparison:
    try:
        return device_adapter_pack_service.compare(
            enterpriseKey, deviceType, baseVersion, targetVersion,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/scenarios", response_model=list[SimulationScenario])
def list_simulation_scenarios() -> list[SimulationScenario]:
    return simulation_service.scenarios()


@router.get("/llm-status", response_model=SimulationLlmStatus)
def get_simulation_llm_status() -> SimulationLlmStatus:
    return simulation_service.llm_status()
