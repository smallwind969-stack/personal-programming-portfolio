"""小型 ASGI 入口鉴权；所有 MCP HTTP 路径都需要独立令牌。"""

from hmac import compare_digest


class BearerTokenASGI:
    def __init__(self, app, token_provider):
        self.app = app
        self.token_provider = token_provider

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        expected = self.token_provider()
        authorization = next(
            (value for name, value in scope.get("headers", ()) if name.lower() == b"authorization"),
            b"",
        )
        prefix = b"Bearer "
        supplied = authorization[len(prefix):] if authorization.startswith(prefix) else b""
        authorized = bool(expected) and bool(supplied) and compare_digest(supplied, expected.encode("utf-8"))
        if not authorized:
            status = 503 if not expected else 401
            await send({"type": "http.response.start", "status": status, "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
            await send({"type": "http.response.body", "body": b"MCP service unavailable" if status == 503 else b"Unauthorized"})
            return

        await self.app(scope, receive, send)
