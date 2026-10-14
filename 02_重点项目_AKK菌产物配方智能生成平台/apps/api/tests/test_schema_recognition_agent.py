from __future__ import annotations

import pytest
import httpx
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pydantic import ValidationError

from app.schema_recognition.contracts import ProviderCandidate, SchemaProviderFailure
from app.schema_recognition.policy import SchemaRecognitionPolicy
from app.schemas.experiments import ExperimentTextFileUploadRequest, SchemaRecognitionCandidate
from app.services.experiment_file_service import ExperimentFileService
from app.services.schema_recognition_agent import SchemaRecognitionAgent
from app.schema_recognition.local_llm_provider import LocalLlmSchemaRecognitionProvider


class FakeProvider:
    provider = "fake-local"
    model = "qwen-test"

    def __init__(self, candidates=None, failure: SchemaProviderFailure | None = None) -> None:
        self.candidates = candidates or []
        self.failure = failure
        self.calls = 0
        self.last_context = None

    def recognize(self, context):
        self.calls += 1
        self.last_context = context
        if self.failure:
            raise self.failure
        return self.candidates


def file_service() -> ExperimentFileService:
    service = ExperimentFileService()
    service.save_text_file(
        "exp-schema",
        ExperimentTextFileUploadRequest(
            fileName="fermenter.csv",
            content="Time,Temp,SecretSignal\n2026-01-01 10:00,37.2,abc\n2026-01-01 10:05,37.4,def\n2026-01-01 10:10,37.5,ghi\n2026-01-01 10:15,37.6,jkl",
        ),
    )
    return service


def test_context_is_bounded_and_excludes_raw_file_and_internal_metadata() -> None:
    context = file_service().build_schema_recognition_context("exp-schema", sample_limit=2)
    assert all(len(field.sampleValues) <= 2 for asset in context.assets for field in asset.fields)
    serialized = context.model_dump_json()
    assert "contentHash" not in serialized
    assert "2026-01-01 10:15" not in serialized
    assert "fermenter.csv" in serialized


def test_candidate_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValidationError):
        SchemaRecognitionCandidate(
            assetId="file-1", originalColumn="Temp", standardField="temperature_c",
            dataType="number", sourceUnit="°C", targetUnit="°C", isTimeField=False,
            confidence=1.2, evidence=["字段别名"], requiresHumanReview=False,
            reviewReasons=[], source="llm",
        )


def test_policy_rejects_unknown_columns_and_marks_unknown_unit_for_review() -> None:
    context = file_service().build_schema_recognition_context("exp-schema", sample_limit=2)
    policy = SchemaRecognitionPolicy()
    accepted, rejected = policy.validate_candidates(context, [
        ProviderCandidate(originalColumn="Missing", standardField="temperature_c", dataType="number", sourceUnit="°C", targetUnit="°C", isTimeField=False, confidence=.9, evidence=["guess"]),
        ProviderCandidate(originalColumn="Temp", standardField="temperature_c", dataType="number", sourceUnit="mystery", targetUnit="mystery", isTimeField=False, confidence=.88, evidence=["device label"]),
    ])
    assert len(rejected) == 1
    assert accepted[0].requiresHumanReview is True
    assert "unknownUnit" in accepted[0].reviewReasons


def test_policy_marks_incompatible_known_unit_dimensions_for_review() -> None:
    context = file_service().build_schema_recognition_context("exp-schema", sample_limit=2)
    accepted, rejected = SchemaRecognitionPolicy().validate_candidates(context, [
        ProviderCandidate(originalColumn="Temp", standardField="temperature_c", dataType="number", sourceUnit="°C", targetUnit="rpm", isTimeField=False, confidence=.9, evidence=["字段"]),
    ])
    assert rejected == []
    assert "unitDimensionConflict" in accepted[0].reviewReasons


def test_agent_merges_matching_rule_and_llm_candidate_without_confirming_mapping() -> None:
    service = file_service()
    asset = service.list_file_assets("exp-schema")[0]
    provider = FakeProvider([ProviderCandidate(
        assetId=asset.assetId, originalColumn="Temp", standardField="temperature_c",
        dataType="number", sourceUnit="°C", targetUnit="°C", isTimeField=False,
        confidence=.91, evidence=["设备字段语义"],
    )])
    agent = SchemaRecognitionAgent(service, provider)
    run = agent.create_run("exp-schema", "command-1")
    assert run.mode == "llm_assisted"
    assert next(item for item in run.candidates if item.originalColumn == "Temp").source == "merged"
    assert service.get_confirmed_field_mappings("exp-schema").mappingCount == 0


def test_provider_failure_falls_back_and_command_is_idempotent() -> None:
    provider = FakeProvider(failure=SchemaProviderFailure("timeout"))
    agent = SchemaRecognitionAgent(file_service(), provider)
    first = agent.create_run("exp-schema", "same-command")
    second = agent.create_run("exp-schema", "same-command")
    assert first.runId == second.runId
    assert first.mode == "rule_fallback"
    assert first.fallbackReason == "timeout"
    assert provider.calls == 1


def test_provider_context_contains_no_key_path_or_unbounded_rows() -> None:
    provider = FakeProvider()
    agent = SchemaRecognitionAgent(file_service(), provider)
    agent.create_run("exp-schema", "privacy-command")
    payload = provider.last_context.model_dump_json()
    assert "apiKey" not in payload
    assert "contentHash" not in payload
    assert "2026-01-01 10:15" not in payload


def test_local_provider_parses_strict_ollama_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        payload = request.read().decode()
        assert "apiKey" not in payload
        return httpx.Response(200, json={"message": {"content": '{"candidates":[{"originalColumn":"Temp","standardField":"temperature_c","dataType":"number","sourceUnit":"°C","targetUnit":"°C","isTimeField":false,"confidence":0.91,"evidence":["字段语义"]}]}'}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = LocalLlmSchemaRecognitionProvider(provider="ollama", model="qwen", base_url="http://local", api_key="", enabled=True, client=client)
    candidates = provider.recognize(file_service().build_schema_recognition_context("exp-schema"))
    assert candidates[0].standardField == "temperature_c"


def test_local_provider_parses_openai_compatible_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"candidates":[{"originalColumn":"Temp","standardField":"temperature_c","dataType":"number","sourceUnit":"℃","targetUnit":"℃","isTimeField":false,"confidence":0.93,"evidence":["设备字段语义"]}]}'}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = LocalLlmSchemaRecognitionProvider(provider="openai_compatible", model="gpt-test", base_url="http://local/v1", api_key="test-key", enabled=True, client=client)
    candidates = provider.recognize(file_service().build_schema_recognition_context("exp-schema"))
    assert candidates[0].confidence == 0.93


def test_local_provider_turns_invalid_json_into_sanitized_failure() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"message": {"content": "not-json"}})))
    provider = LocalLlmSchemaRecognitionProvider(provider="ollama", model="qwen", base_url="http://user:secret@local/v1", api_key="secret", enabled=True, client=client)
    with pytest.raises(SchemaProviderFailure) as error:
        provider.recognize(file_service().build_schema_recognition_context("exp-schema"))
    assert error.value.category == "invalidResponse"
    assert "secret" not in str(error.value)


def test_local_provider_rejects_unexpected_control_fields() -> None:
    content = '{"candidates":[{"originalColumn":"Temp","standardField":"temperature_c","dataType":"number","isTimeField":false,"confidence":0.9,"evidence":["字段"],"deviceCommand":"set temperature"}]}'
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"message": {"content": content}})))
    provider = LocalLlmSchemaRecognitionProvider(provider="ollama", model="qwen", base_url="http://local", api_key="", enabled=True, client=client)
    with pytest.raises(SchemaProviderFailure) as error:
        provider.recognize(file_service().build_schema_recognition_context("exp-schema"))
    assert error.value.category == "invalidResponse"


def test_schema_recognition_api_create_get_and_no_auto_confirmation(monkeypatch) -> None:
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.schema_recognition_agent import schema_recognition_agent

    service = schema_recognition_agent.file_service
    service.save_text_file("exp-schema-api", ExperimentTextFileUploadRequest(fileName="device.csv", content="Time,Temp\n10:00,37.2"))
    schema_recognition_agent._runs.clear()
    schema_recognition_agent._commands.clear()
    monkeypatch.setattr(schema_recognition_agent, "provider", FakeProvider())
    client = TestClient(app)
    created = client.post("/experiments/exp-schema-api/schema-recognition-runs", json={"commandId": "api-command"})
    assert created.status_code == 200
    body = created.json()
    fetched = client.get(f"/experiments/exp-schema-api/schema-recognition-runs/{body['runId']}")
    assert fetched.status_code == 200
    assert fetched.json() == body
    assert service.get_confirmed_field_mappings("exp-schema-api").mappingCount == 0
    assert client.get("/experiments/exp-schema-api/schema-recognition-runs/missing").status_code == 404


def test_analysis_workflow_executes_schema_agent_at_schema_node(monkeypatch) -> None:
    from app.services.agent_orchestrator import AgentOrchestrator
    from app.agent_runtime.deterministic import DeterministicRuntimeAdapter
    from app.services.schema_recognition_agent import schema_recognition_agent

    schema_recognition_agent._runs.clear()
    schema_recognition_agent._commands.clear()
    monkeypatch.setattr(schema_recognition_agent, "provider", FakeProvider())
    orchestrator = AgentOrchestrator(runtime=DeterministicRuntimeAdapter(), runtime_backend="deterministic")
    run = orchestrator.create_run("exp-schema")
    run = orchestrator.advance("exp-schema", run.runId, run.runtimeRevision, "advance-collect")
    assert run.currentNodeId == "schema-recognition"
    run = orchestrator.advance("exp-schema", run.runId, run.runtimeRevision, "advance-schema")
    snapshot = orchestrator._runtime.get(run.runtimeRunId)
    assert snapshot.state["schemaRecognition"]["runId"].startswith("schema-run-")
    assert snapshot.state["schemaRecognition"]["mode"] == "llm_assisted"
    assert schema_recognition_agent.get_run("exp-schema", snapshot.state["schemaRecognition"]["runId"]) is not None


def test_different_experiments_can_call_provider_in_parallel() -> None:
    service = file_service()
    service.save_text_file("exp-schema-2", ExperimentTextFileUploadRequest(fileName="device.csv", content="Time,Temp\n10:00,36.8"))
    barrier = Barrier(2, timeout=1)

    class ParallelProvider(FakeProvider):
        def recognize(self, context):
            self.calls += 1
            barrier.wait()
            return []

    provider = ParallelProvider()
    agent = SchemaRecognitionAgent(service, provider)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(agent.create_run, experiment_id, f"cmd-{experiment_id}") for experiment_id in ("exp-schema", "exp-schema-2")]
        assert all(future.result().status == "completed" for future in futures)
    assert provider.calls == 2


def test_same_command_concurrently_shares_one_provider_call() -> None:
    from threading import Event
    release = Event()

    class WaitingProvider(FakeProvider):
        def recognize(self, context):
            self.calls += 1
            release.wait(timeout=1)
            return []

    provider = WaitingProvider()
    agent = SchemaRecognitionAgent(file_service(), provider)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(agent.create_run, "exp-schema", "shared-command")
        second = pool.submit(agent.create_run, "exp-schema", "shared-command")
        release.set()
        assert first.result().runId == second.result().runId
    assert provider.calls == 1
