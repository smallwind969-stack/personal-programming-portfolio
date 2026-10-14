from fastapi.testclient import TestClient

from app.main import app
from app.agent_runtime.factory import build_runtime_adapter
from app.agent_runtime.langgraph_adapter import LangGraphRuntimeAdapter
from app.agent_runtime.deterministic import DeterministicRuntimeAdapter
from app.agent_runtime.sqlite_persistent import PersistentRuntimeAdapter


client = TestClient(app)


def test_runtime_status_discloses_real_backend_and_local_model_without_secret() -> None:
    response = client.get("/agent-runtime/status")
    assert response.status_code == 200
    body = response.json()
    assert body["effectiveBackend"] in {"deterministic", "langgraph"}
    langgraph = next(item for item in body["backends"] if item["backend"] == "langgraph")
    assert langgraph["installed"] is True
    assert langgraph["version"] == "1.2.9"
    assert body["localModel"]["provider"]
    assert body["localModel"]["liveProbeEndpoint"] == "/llm/status"
    assert "apiKey" not in str(body)
    assert body["executionBoundary"]


def test_runtime_factory_selects_real_langgraph_and_has_safe_fallback(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_BACKEND", "langgraph")
    adapter, backend, reason = build_runtime_adapter()
    assert isinstance(adapter, LangGraphRuntimeAdapter)
    assert backend == "langgraph"
    assert reason is None
    monkeypatch.setattr("app.agent_runtime.factory.langgraph_installed", lambda: False)
    fallback, backend, reason = build_runtime_adapter()
    assert isinstance(fallback, DeterministicRuntimeAdapter)
    assert backend == "deterministic"
    assert reason


def test_runtime_factory_enables_sqlite_persistence_when_path_is_configured(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_BACKEND", "deterministic")
    monkeypatch.setenv("AGENT_RUNTIME_CHECKPOINT_PATH", str(tmp_path / "runtime.db"))
    adapter, backend, reason = build_runtime_adapter()
    assert isinstance(adapter, PersistentRuntimeAdapter)
    assert backend == "deterministic-sqlite"
    assert reason is None
