from __future__ import annotations

import json

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.feature_binding_advisor.contracts import BindingAdvisorContext, BindingLlmCandidate
from app.feature_binding_advisor.providers import BindingProviderFailure


class _BindingProviderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidates: list[BindingLlmCandidate]


class LocalLlmBindingSuggestionProvider:
    def __init__(self, *, provider: str, model: str, base_url: str, api_key: str,
                 enabled: bool, timeout: float = 45, client: httpx.Client | None = None) -> None:
        self.provider, self.model, self.enabled = provider, model, enabled
        self.baseUrl, self.apiKey = base_url.rstrip("/"), api_key
        self.timeout, self.client = timeout, client or httpx.Client()

    def suggest(self, context: BindingAdvisorContext) -> list[BindingLlmCandidate]:
        if not self.enabled:
            raise BindingProviderFailure("providerDisabled")
        prompt = json.dumps({
            "task": "为已确认的标准字段和模型特征提出仿真参数绑定候选；仅返回 JSON，不激活绑定，不输出设备控制指令。",
            "allowedSimulationParameters": ["carbonConcentration", "cultureHours", "temperatureC", "ph", "anaerobicScore", "pressureMpa", "stirringRpm"],
            "outputSchema": {"candidates": [{
                "modelFeature": "must exist in featureNames", "simulationParameter": "allowed value",
                "confidence": "0..1", "evidence": ["verifiable reason"], "scale": 1.0, "offset": 0.0,
            }]},
            "context": context.model_dump(mode="json"),
        }, ensure_ascii=False)
        try:
            if self.provider == "ollama":
                response = self.client.post(f"{self.baseUrl}/api/chat", json={
                    "model": self.model, "stream": False, "format": "json",
                    "options": {"temperature": 0.1, "num_predict": 1000},
                    "messages": [{"role": "system", "content": "只输出合法 JSON；禁止设备控制。"}, {"role": "user", "content": prompt}],
                }, timeout=self.timeout)
                response.raise_for_status(); content = response.json()["message"]["content"]
            else:
                headers = {"Authorization": f"Bearer {self.apiKey}"} if self.apiKey else None
                response = self.client.post(f"{self.baseUrl}/chat/completions", headers=headers, json={
                    "model": self.model, "temperature": 0.1,
                    "messages": [{"role": "system", "content": "只输出合法 JSON；禁止设备控制。"}, {"role": "user", "content": prompt}],
                }, timeout=self.timeout)
                response.raise_for_status(); content = response.json()["choices"][0]["message"]["content"]
            return _BindingProviderResponse.model_validate_json(content).candidates
        except httpx.TimeoutException as exc:
            raise BindingProviderFailure("timeout") from exc
        except httpx.HTTPError as exc:
            raise BindingProviderFailure("providerUnavailable") from exc
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, ValidationError) as exc:
            raise BindingProviderFailure("invalidResponse") from exc
