from __future__ import annotations

import json

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.schema_recognition.contracts import ProviderCandidate, SchemaProviderFailure, SchemaRecognitionContext


class _ProviderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidates: list[ProviderCandidate]


class LocalLlmSchemaRecognitionProvider:
    def __init__(self, *, provider: str, model: str, base_url: str, api_key: str, enabled: bool, timeout: float = 45, client: httpx.Client | None = None) -> None:
        self.provider, self.model = provider, model
        self.base_url, self.api_key, self.enabled = base_url.rstrip("/"), api_key, enabled
        self.timeout, self.client = timeout, client or httpx.Client()

    def recognize(self, context: SchemaRecognitionContext) -> list[ProviderCandidate]:
        if not self.enabled:
            raise SchemaProviderFailure("providerDisabled")
        prompt = json.dumps({
            "task": "识别设备数据字段，仅返回结构化候选，不执行清洗、建模或设备控制。",
            "outputSchema": {"candidates": [{
                "assetId": "optional", "originalColumn": "string", "standardField": "snake_case",
                "dataType": "number|string|datetime|boolean", "sourceUnit": "optional",
                "targetUnit": "optional", "isTimeField": "boolean", "confidence": "0..1", "evidence": ["可验证依据"],
            }]},
            "context": context.model_dump(),
        }, ensure_ascii=False)
        try:
            if self.provider == "ollama":
                response = self.client.post(f"{self.base_url}/api/chat", json={
                    "model": self.model, "stream": False, "format": "json",
                    "options": {"temperature": 0.1, "num_predict": 1200},
                    "messages": [{"role": "system", "content": "只输出合法 JSON，不输出思维链。"}, {"role": "user", "content": prompt}],
                }, timeout=self.timeout)
                response.raise_for_status()
                content = response.json()["message"]["content"]
            else:
                headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
                response = self.client.post(f"{self.base_url}/chat/completions", headers=headers, json={
                    "model": self.model, "temperature": 0.1,
                    "messages": [{"role": "system", "content": "只输出合法 JSON，不输出思维链。"}, {"role": "user", "content": prompt}],
                }, timeout=self.timeout)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
            return _ProviderResponse.model_validate_json(content).candidates
        except httpx.TimeoutException as exc:
            raise SchemaProviderFailure("timeout") from exc
        except httpx.HTTPError as exc:
            raise SchemaProviderFailure("providerUnavailable") from exc
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, ValidationError) as exc:
            raise SchemaProviderFailure("invalidResponse") from exc
