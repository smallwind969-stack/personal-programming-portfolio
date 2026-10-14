"""受控病例 ID 与模型服务之间的最小 HTTP 边界。"""

import httpx


class ToolServiceError(RuntimeError):
    """可向工具调用者展示、但不包含本地路径和服务响应体的错误。"""

    def __init__(self, message: str, code: str = "MODEL_SERVICE_UNAVAILABLE"):
        super().__init__(message)
        self.code = code


class ModelToolClient:
    def __init__(self, base_url: str, token: str, transport=None):
        if not token:
            raise ToolServiceError("模型服务令牌尚未配置")
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.transport = transport

    def _post(self, path: str, payload: dict) -> dict:
        try:
            with httpx.Client(transport=self.transport, timeout=600.0) as client:
                response = client.post(
                    f"{self.base_url}{path}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.token}"},
                )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            code = {
                400: "INVALID_CANDIDATE_IDS",
                404: "CASE_NOT_REGISTERED",
                409: "RUN_EXPIRED",
            }.get(status, "MODEL_SERVICE_UNAVAILABLE")
            raise ToolServiceError(f"模型服务请求失败（HTTP {status}）", code=code) from None
        except (httpx.HTTPError, ValueError):
            raise ToolServiceError("模型服务请求失败；请检查服务状态和日志") from None

    def detect(self, case_id: str) -> dict:
        return self._post("/detect", {"case_id": case_id})

    def classify(self, case_id: str, run_id: str, candidate_ids: list[str]) -> dict:
        return self._post(
            "/identify",
            {"case_id": case_id, "run_id": run_id, "candidate_ids": candidate_ids},
        )
