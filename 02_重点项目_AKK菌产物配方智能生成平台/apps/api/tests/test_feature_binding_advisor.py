from app.feature_binding_advisor.agent import FeatureBindingAdvisorAgent
from app.feature_binding_advisor.contracts import (
    BindingAdvisorContext, BindingLlmCandidate, DeviceAdapterPackSelector,
)
from app.feature_binding_advisor.adapter_pack import DeviceAdapterPack, DeviceAdapterEntry
from app.feature_binding_advisor.providers import BindingSuggestionProvider, NullBindingSuggestionProvider
from app.feature_binding_advisor.local_llm_provider import LocalLlmBindingSuggestionProvider
from app.feature_binding_advisor.providers import BindingProviderFailure
from app.feature_binding_advisor.store import SqliteFeatureBindingSuggestionStore
import httpx
import pytest


def context() -> BindingAdvisorContext:
    return BindingAdvisorContext(
        experimentId="exp-real", modelVersion="model-v1",
        featureNames=["temperature_c", "ph", "custom_signal"],
        confirmedStandardFields={"temperature_c": "℃", "ph": "pH", "custom_signal": "a.u."},
        featureRanges={"temperature_c": {"min": 35, "max": 39}, "ph": {"min": 6.2, "max": 7.2}, "custom_signal": {"min": 0, "max": 1}},
    )


def test_rule_advisor_covers_model_features_and_routes_unknown_to_human_review() -> None:
    agent = FeatureBindingAdvisorAgent(lambda *_: context(), NullBindingSuggestionProvider())
    run = agent.create_run("exp-real", "model-v1", "command-1")
    assert run.mode == "rule_only" and len(run.candidates) == 3
    temperature = next(item for item in run.candidates if item.modelFeature == "temperature_c")
    assert temperature.simulationParameter == "temperatureC" and temperature.requiresHumanReview is False
    unknown = next(item for item in run.candidates if item.modelFeature == "custom_signal")
    assert unknown.simulationParameter is None and unknown.requiresHumanReview is True
    assert run.readyForConfirmation is False and run.activatedBindingVersion is None
    assert agent.create_run("exp-real", "model-v1", "command-1").runId == run.runId


def test_llm_conflict_and_invalid_candidates_are_audited_not_activated() -> None:
    class Provider(BindingSuggestionProvider):
        provider = "local"; model = "test-model"; enabled = True
        def suggest(self, ctx):
            return [
                BindingLlmCandidate(modelFeature="temperature_c", simulationParameter="stirringRpm", confidence=0.91, evidence=["semantic guess"]),
                BindingLlmCandidate(modelFeature="not_in_model", simulationParameter="ph", confidence=0.99, evidence=["invalid feature"]),
            ]
    run = FeatureBindingAdvisorAgent(lambda *_: context(), Provider()).create_run("exp-real", "model-v1", "command-2")
    temperature = next(item for item in run.candidates if item.modelFeature == "temperature_c")
    assert run.mode == "llm_assisted" and run.conflictCount == 1 and run.rejectedCount == 1
    assert temperature.simulationParameter == "temperatureC"
    assert temperature.requiresHumanReview and "providerConflict" in temperature.reviewReasons
    assert run.activatedBindingVersion is None


def test_local_llm_provider_parses_strict_ollama_json_without_raw_data() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode("utf-8")
        assert request.url.path == "/api/chat" and "apiKey" not in body and "rawRows" not in body
        return httpx.Response(200, json={"message": {"content": '{"candidates":[{"modelFeature":"custom_signal","simulationParameter":"anaerobicScore","confidence":0.82,"evidence":["企业字段语义"]}]}'}})
    provider = LocalLlmBindingSuggestionProvider(
        provider="ollama", model="qwen", base_url="http://local", api_key="", enabled=True,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result = provider.suggest(context())
    assert result[0].modelFeature == "custom_signal" and result[0].simulationParameter == "anaerobicScore"


def test_local_llm_provider_rejects_control_fields_and_agent_records_sanitized_fallback() -> None:
    content = '{"candidates":[{"modelFeature":"custom_signal","simulationParameter":"anaerobicScore","confidence":0.9,"evidence":["guess"],"deviceCommand":"set speed"}]}'
    provider = LocalLlmBindingSuggestionProvider(
        provider="ollama", model="qwen", base_url="http://user:secret@local", api_key="secret", enabled=True,
        client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"message": {"content": content}}))),
    )
    with pytest.raises(BindingProviderFailure) as error:
        provider.suggest(context())
    assert error.value.category == "invalidResponse" and "secret" not in str(error.value)
    run = FeatureBindingAdvisorAgent(lambda *_: context(), provider).create_run("exp-real", "model-v1", "fallback")
    assert run.mode == "rule_fallback" and run.fallbackReason == "invalidResponse"


def test_suggestion_run_is_idempotent_and_visible_across_agent_processes(tmp_path) -> None:
    database = tmp_path / "binding-suggestions.db"
    first = FeatureBindingAdvisorAgent(
        lambda *_: context(), NullBindingSuggestionProvider(),
        store=SqliteFeatureBindingSuggestionStore(str(database)),
    )
    created = first.create_run("exp-real", "model-v1", "persistent-command")

    second = FeatureBindingAdvisorAgent(
        lambda *_: context(), NullBindingSuggestionProvider(),
        store=SqliteFeatureBindingSuggestionStore(str(database)),
    )
    repeated = second.create_run("exp-real", "model-v1", "persistent-command")

    assert repeated.runId == created.runId
    assert second.get_run("exp-real", created.runId) == created


def adapter_pack(entries: list[DeviceAdapterEntry]) -> DeviceAdapterPack:
    return DeviceAdapterPack(
        packId="adapter-enterprise-a-reactor-1.0.0", enterpriseKey="enterprise-a",
        deviceType="reactor", packVersion="1.0.0", entries=entries, createdBy="owner",
        createdAt="2026-07-20T00:00:00Z", contentHash="sha256:" + "a" * 64,
    )


def test_selected_adapter_pack_maps_unknown_feature_before_llm() -> None:
    pack = adapter_pack([
        DeviceAdapterEntry(
            sourceFieldAlias="CustomSignal", standardField="custom_signal",
            simulationParameter="anaerobicScore", sourceUnit="a.u.", targetUnit=None,
            scale=2.0, offset=-1.0,
        ),
    ])
    selector = DeviceAdapterPackSelector(
        enterpriseKey="enterprise-a", deviceType="reactor", packVersion="1.0.0",
    )
    agent = FeatureBindingAdvisorAgent(
        lambda *_: context(), NullBindingSuggestionProvider(),
        adapter_pack_provider=lambda selected: pack,
    )

    run = agent.create_run("exp-real", "model-v1", "adapter-command", selector)

    custom = next(item for item in run.candidates if item.modelFeature == "custom_signal")
    assert custom.source == "adapter"
    assert custom.simulationParameter == "anaerobicScore"
    assert custom.scale == 2.0 and custom.offset == -1.0
    assert run.adapterPack is not None
    assert run.adapterPack.contentHash == pack.contentHash


def test_adapter_rule_conflict_is_explicit_and_command_cannot_switch_pack(tmp_path) -> None:
    conflicting = adapter_pack([
        DeviceAdapterEntry(
            sourceFieldAlias="Temp", standardField="temperature_c",
            simulationParameter="stirringRpm", sourceUnit="℃", targetUnit="rpm",
        ),
    ])
    selector = DeviceAdapterPackSelector(
        enterpriseKey="enterprise-a", deviceType="reactor", packVersion="1.0.0",
    )
    store = SqliteFeatureBindingSuggestionStore(str(tmp_path / "suggestions.db"))
    agent = FeatureBindingAdvisorAgent(
        lambda *_: context(), NullBindingSuggestionProvider(), store=store,
        adapter_pack_provider=lambda selected: conflicting,
    )
    run = agent.create_run("exp-real", "model-v1", "same-command", selector)
    temperature = next(item for item in run.candidates if item.modelFeature == "temperature_c")
    assert temperature.source == "adapter"
    assert temperature.simulationParameter == "stirringRpm"
    assert temperature.requiresHumanReview
    assert "adapterRuleConflict" in temperature.reviewReasons

    changed = selector.model_copy(update={"packVersion": "2.0.0"})
    with pytest.raises(ValueError, match="different adapter pack"):
        agent.create_run("exp-real", "model-v1", "same-command", changed)
