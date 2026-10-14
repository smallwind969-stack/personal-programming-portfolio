import json

import app.services.llm_service as llm_module
from app.services.llm_service import LocalLlmService


class Response:
    def __init__(self, status_code: int):
        self.status_code = status_code


def test_remote_compatible_status_is_sanitized_and_classifies_auth_failure(monkeypatch) -> None:
    secret = "secret-value-that-must-never-leak"
    monkeypatch.setenv("LOCAL_LLM_ENABLED", "true")
    monkeypatch.setenv("LOCAL_LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "https://user:pass@example.test/v1?token=hidden")
    monkeypatch.setenv("LOCAL_LLM_API_KEY", secret)
    monkeypatch.setenv("LOCAL_LLM_MODEL", "compatible-model")
    monkeypatch.setenv("PRODUCT_INNOVATION_LLM_ENABLED", "true")
    monkeypatch.setattr(llm_module.httpx, "get", lambda *_args, **_kwargs: Response(401))

    status = LocalLlmService().status()
    serialized = json.dumps(status.model_dump(mode="json"), ensure_ascii=False)

    assert status.available is False
    assert status.failureCategory == "authentication"
    assert status.apiKeyConfigured is True
    assert status.endpointScope == "remote"
    assert status.baseUrl == "https://example.test/v1"
    assert secret not in serialized and "pass" not in serialized and "hidden" not in serialized
    assert next(route for route in status.usageRoutes if route.routeKey == "productInnovation").enabled is True


def test_disabled_model_does_not_probe_network_and_reports_rule_fallback(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_ENABLED", "false")
    monkeypatch.setattr(
        llm_module.httpx, "get",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("disabled service must not probe")),
    )

    status = LocalLlmService().status()

    assert status.available is False
    assert status.failureCategory == "disabled"
    assert status.mode == "rule_fallback"
    assert status.latencyMs is None
