"""OpenAI 兼容入口到 Ollama 原生无思考模式的契约测试。"""

import json
import sys
from pathlib import Path

import httpx
from fastapi.testclient import TestClient


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import app  # noqa: E402


def _native_reply(content="<code>print(detect_lung_nodules(case_id='demo-001'))</code>"):
    return {"model": "qwen3:8b", "message": {"role": "assistant", "content": content}, "done": True,
            "done_reason": "stop", "prompt_eval_count": 21, "eval_count": 12}


def test_chat_forces_native_think_false_and_translates_text_parts(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
    monkeypatch.setenv("ADAPTER_MODEL_ID", "qwen3:8b")
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=_native_reply())

    app.state.ollama_transport = httpx.MockTransport(handler)
    try:
        response = TestClient(app).post("/v1/chat/completions", json={
            "model": "qwen3:8b", "stream": False, "temperature": 0,
            "messages": [{"role": "user", "content": [{"type": "text", "text": "Run demo-001"}]}],
        })
    finally:
        app.state.ollama_transport = None
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"].startswith("<code>")
    assert seen[0].url.path == "/api/chat"
    payload = json.loads(seen[0].content)
    assert payload["think"] is False
    assert payload["stream"] is False
    assert payload["messages"] == [{"role": "user", "content": "Run demo-001"}]
    assert payload["options"]["temperature"] == 0


def test_streaming_request_emits_openai_sse_chunks(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODEL_ID", "qwen3:8b")
    app.state.ollama_transport = httpx.MockTransport(lambda request: httpx.Response(200, json=_native_reply()))
    try:
        response = TestClient(app).post("/v1/chat/completions", json={
            "model": "qwen3:8b", "stream": True,
            "messages": [{"role": "user", "content": "Run demo-001"}],
            "stream_options": {"include_usage": True},
        })
    finally:
        app.state.ollama_transport = None
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    frames = [line.removeprefix("data: ") for line in response.text.splitlines() if line.startswith("data: ")]
    assert frames[-1] == "[DONE]"
    chunks = [json.loads(frame) for frame in frames[:-1]]
    assert any(chunk.get("choices") and chunk["choices"][0]["delta"].get("content", "").startswith("<code>") for chunk in chunks)
    assert any(chunk.get("usage", {}).get("completion_tokens") == 12 for chunk in chunks)


def test_rejects_thinking_markup_in_native_answer(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODEL_ID", "qwen3:8b")
    app.state.ollama_transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=_native_reply("<think>hidden</think><code>print(1)</code>"))
    )
    try:
        response = TestClient(app).post("/v1/chat/completions", json={
            "model": "qwen3:8b", "messages": [{"role": "user", "content": "run"}],
        })
    finally:
        app.state.ollama_transport = None
    assert response.status_code == 502
    assert "hidden" not in response.text


def test_rejects_unexpected_model_and_non_text_parts(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODEL_ID", "qwen3:8b")
    client = TestClient(app)
    wrong_model = client.post("/v1/chat/completions", json={
        "model": "other", "messages": [{"role": "user", "content": "run"}],
    })
    image_input = client.post("/v1/chat/completions", json={
        "model": "qwen3:8b", "messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}]}],
    })
    assert wrong_model.status_code == 400
    assert image_input.status_code == 422


def test_models_endpoint_lists_only_allowed_model(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODEL_ID", "qwen3:8b")
    response = TestClient(app).get("/v1/models")
    assert response.status_code == 200
    assert [model["id"] for model in response.json()["data"]] == ["qwen3:8b"]
