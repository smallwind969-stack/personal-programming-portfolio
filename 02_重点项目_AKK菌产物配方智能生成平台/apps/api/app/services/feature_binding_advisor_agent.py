from __future__ import annotations

import os

from app.feature_binding_advisor.agent import FeatureBindingAdvisorAgent
from app.feature_binding_advisor.contracts import BindingAdvisorContext
from app.feature_binding_advisor.local_llm_provider import LocalLlmBindingSuggestionProvider
from app.feature_binding_advisor.store import SqliteFeatureBindingSuggestionStore
from app.feature_binding_advisor.adapter_pack import (
    DeviceAdapterPackService, SqliteDeviceAdapterPackStore,
)
from app.research.service import promoted_model_registry
from app.services.experiment_file_service import experiment_file_service
from app.services.llm_service import local_llm_service


def build_binding_advisor_context(experiment_id: str, model_version: str) -> BindingAdvisorContext:
    model = promoted_model_registry.get(experiment_id, model_version)
    if model is None:
        raise LookupError("approved model version was not found")
    confirmed = experiment_file_service.get_confirmed_field_mappings(experiment_id)
    units = {mapping.standardField: mapping.unit for mapping in confirmed.mappings}
    return BindingAdvisorContext(
        experimentId=experiment_id, modelVersion=model_version, featureNames=model.featureNames,
        confirmedStandardFields={feature: units.get(feature) for feature in model.featureNames},
        featureRanges={key: value.model_dump(mode="json") for key, value in model.featureRanges.items()},
    )


device_adapter_pack_service = DeviceAdapterPackService(SqliteDeviceAdapterPackStore(
    os.getenv("DEVICE_ADAPTER_PACK_STORE_PATH", "data/runtime/device-adapter-packs.db")
))


feature_binding_advisor = FeatureBindingAdvisorAgent(
    build_binding_advisor_context,
    LocalLlmBindingSuggestionProvider(
        provider=local_llm_service.provider, model=local_llm_service.model,
        base_url=local_llm_service.base_url, api_key=local_llm_service.api_key,
        enabled=local_llm_service.enabled and os.getenv("FEATURE_BINDING_LLM_ENABLED", "false").lower() == "true",
        timeout=local_llm_service.timeout,
    ),
    store=SqliteFeatureBindingSuggestionStore(
        os.getenv("FEATURE_BINDING_SUGGESTION_STORE_PATH", "data/runtime/feature-binding-suggestions.db")
    ),
    adapter_pack_provider=lambda selector: device_adapter_pack_service.get_verified(
        selector.enterpriseKey, selector.deviceType, selector.packVersion,
    ),
)
