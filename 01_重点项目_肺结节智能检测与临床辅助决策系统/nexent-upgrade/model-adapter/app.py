"""本机 Nexent/OpenAI 请求到 Ollama 原生无思考模式的最小适配。"""

import json
import os
import time
from uuid import uuid4

import httpx
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import StreamingResponse


app = FastAPI(title="Local Ollama CodeAgent Adapter")


def _model_id():
    return os.getenv("ADAPTER_MODEL_ID", "qwen3:8b")


def _text_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list) and all(isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str) for part in content):
        return "\n".join(part["text"] for part in content)
    raise HTTPException(status_code=422, detail="仅支持文本消息")


def _ollama_request(payload):
    if payload.get("model") != _model_id():
        raise HTTPException(status_code=400, detail="模型不在本机适配范围内")
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        raise HTTPException(status_code=422, detail="缺少消息")
    if payload.get("tools") or payload.get("functions"):
        raise HTTPException(status_code=422, detail="此适配层仅支持 Nexent CodeAgent 文本协议")
    normalized = []
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in {"system", "developer", "user", "assistant", "tool"}:
            raise HTTPException(status_code=422, detail="消息角色无效")
        normalized.append({"role": message["role"], "content": _text_content(message.get("content"))})
    options = {}
    for source, target in (("temperature", "temperature"), ("top_p", "top_p"), ("max_tokens", "num_predict"), ("seed", "seed")):
        if payload.get(source) is not None:
            options[target] = payload[source]
    return {"model": _model_id(), "messages": normalized, "think": False, "stream": False, "options": options}


def _ollama_reply(request_payload):
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    try:
        with httpx.Client(transport=getattr(app.state, "ollama_transport", None), timeout=300.0) as client:
            response = client.post(f"{base_url}/api/chat", json=request_payload)
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(status_code=502, detail="Ollama 原生接口不可用") from None
    content = result.get("message", {}).get("content")
    if not isinstance(content, str) or "<think" in content.lower() or "</think" in content.lower():
        raise HTTPException(status_code=502, detail="模型输出含未受支持的思考标记")
    return result, content


def _usage(result):
    prompt = result.get("prompt_eval_count", 0) or 0
    completion = result.get("eval_count", 0) or 0
    return {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": prompt + completion}


def _sse(data):
    return "data: " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n\n"


@app.get("/v1/models")
def list_models():
    return {"object": "list", "data": [{"id": _model_id(), "object": "model", "owned_by": "local-ollama"}]}


@app.post("/v1/chat/completions")
def chat_completions(payload: dict = Body(...)):
    native_request = _ollama_request(payload)
    result, content = _ollama_reply(native_request)
    created = int(time.time())
    chat_id = "chatcmpl-local-" + uuid4().hex
    model = _model_id()
    finish_reason = "length" if result.get("done_reason") == "length" else "stop"
    usage = _usage(result)
    if not payload.get("stream", False):
        return {
            "id": chat_id, "object": "chat.completion", "created": created, "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": finish_reason}],
            "usage": usage,
        }

    def chunks():
        common = {"id": chat_id, "object": "chat.completion.chunk", "created": created, "model": model}
        yield _sse({**common, "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]})
        yield _sse({**common, "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}]})
        yield _sse({**common, "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}]})
        if payload.get("stream_options", {}).get("include_usage"):
            yield _sse({**common, "choices": [], "usage": usage})
        yield "data: [DONE]\n\n"

    return StreamingResponse(chunks(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("ADAPTER_PORT", "11435")))
