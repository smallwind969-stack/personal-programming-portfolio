import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from http_auth import BearerTokenASGI


def _call(headers, token="demo-secret", path="/mcp"):
    forwarded = []
    messages = []

    async def inner(scope, receive, send):
        forwarded.append(scope)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    app = BearerTokenASGI(inner, lambda: token)
    scope = {"type": "http", "path": path, "headers": headers}
    task = app(scope, receive, send)
    try:
        task.send(None)
    except StopIteration:
        pass
    else:
        raise AssertionError("测试用 ASGI 响应意外地等待了异步 I/O")
    return forwarded, messages


def test_missing_or_wrong_token_is_rejected():
    for headers in ([], [(b"authorization", b"Bearer wrong")]):
        forwarded, messages = _call(headers)
        assert not forwarded
        assert messages[0]["status"] == 401


def test_config_missing_fails_closed():
    forwarded, messages = _call([(b"authorization", b"Bearer any")], token="")
    assert not forwarded
    assert messages[0]["status"] == 503


def test_valid_token_forwards_to_mcp_app():
    forwarded, messages = _call([(b"authorization", b"Bearer demo-secret")])
    assert len(forwarded) == 1
    assert messages[0]["status"] == 200


def test_other_http_paths_are_protected_too():
    forwarded, messages = _call([(b"authorization", b"Bearer wrong")], path="/messages")
    assert not forwarded
    assert messages[0]["status"] == 401
