from __future__ import annotations

import json
import httpx
from pydantic import ValidationError

from app.result_interpretation.contracts import InterpretationProviderOutput, ResultInterpretationContext, ResultInterpretationProviderFailure


class LocalLlmResultInterpretationProvider:
    def __init__(self, *, provider: str, model: str, base_url: str, api_key: str, enabled: bool, timeout: float = 45, client: httpx.Client | None = None) -> None:
        self.provider, self.model, self.base_url = provider, model, base_url.rstrip("/")
        self.api_key, self.enabled, self.timeout, self.client = api_key, enabled, timeout, client or httpx.Client()

    def interpret(self, context: ResultInterpretationContext) -> InterpretationProviderOutput:
        if not self.enabled: raise ResultInterpretationProviderFailure("providerDisabled")
        prompt = json.dumps({
            "task": "解释权威实验指标并提出下一轮研发实验建议。不得输出指标值、仿真准入决定、模型晋升或设备控制指令。",
            "outputSchema": InterpretationProviderOutput.model_json_schema(),
            "context": context.model_dump(),
            "allowedEvidenceRefs": sorted(context.allowed_evidence_refs()),
        }, ensure_ascii=False)
        try:
            messages = [{"role": "system", "content": "只输出符合既定结构的 JSON，不输出隐藏思维链。"}, {"role": "user", "content": prompt}]
            if self.provider == "ollama":
                response = self.client.post(f"{self.base_url}/api/chat", json={"model": self.model, "stream": False, "format": "json", "options": {"temperature": .1, "num_predict": 1600}, "messages": messages}, timeout=self.timeout)
                response.raise_for_status(); content = response.json()["message"]["content"]
            else:
                headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
                response = self.client.post(f"{self.base_url}/chat/completions", headers=headers, json={"model": self.model, "temperature": .1, "messages": messages}, timeout=self.timeout)
                response.raise_for_status(); content = response.json()["choices"][0]["message"]["content"]
            return InterpretationProviderOutput.model_validate_json(content)
        except httpx.TimeoutException as exc: raise ResultInterpretationProviderFailure("timeout") from exc
        except httpx.HTTPError as exc: raise ResultInterpretationProviderFailure("providerUnavailable") from exc
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, ValidationError) as exc: raise ResultInterpretationProviderFailure("invalidResponse") from exc
