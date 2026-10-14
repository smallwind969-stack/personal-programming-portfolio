from __future__ import annotations

import json
import httpx
from pydantic import ValidationError

from app.product_innovation.contracts import InnovationProviderFailure, InnovationProviderOutput, ProductInnovationContext


class LocalLlmProductInnovationProvider:
    def __init__(self, *, provider: str, model: str, base_url: str, api_key: str, enabled: bool, timeout: float = 45, client: httpx.Client | None = None) -> None:
        self.provider, self.model, self.base_url = provider, model, base_url.rstrip("/")
        self.api_key, self.enabled, self.timeout, self.client = api_key, enabled, timeout, client or httpx.Client()

    def innovate(self, context: ProductInnovationContext) -> InnovationProviderOutput:
        if not self.enabled: raise InnovationProviderFailure("providerDisabled")
        prompt = json.dumps({
            "task": "将产品构想转换成结构化研发需求画像。不得生成最终配方、原料比例、医疗承诺、生产参数或设备控制指令。成本只能作为待验证假设。",
            "outputSchema": InnovationProviderOutput.model_json_schema(),
            "allowedEvidenceRefs": sorted(context.allowed_evidence_refs()),
            "context": context.model_dump(),
        }, ensure_ascii=False)
        try:
            messages = [{"role": "system", "content": "只输出合法 JSON，不输出隐藏思维链。"}, {"role": "user", "content": prompt}]
            if self.provider == "ollama":
                response = self.client.post(f"{self.base_url}/api/chat", json={"model": self.model, "stream": False, "format": "json", "options": {"temperature": .2, "num_predict": 1800}, "messages": messages}, timeout=self.timeout)
                response.raise_for_status(); content = response.json()["message"]["content"]
            else:
                headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
                response = self.client.post(f"{self.base_url}/chat/completions", headers=headers, json={"model": self.model, "temperature": .2, "messages": messages}, timeout=self.timeout)
                response.raise_for_status(); content = response.json()["choices"][0]["message"]["content"]
            return InnovationProviderOutput.model_validate_json(content)
        except httpx.TimeoutException as exc: raise InnovationProviderFailure("timeout") from exc
        except httpx.HTTPError as exc: raise InnovationProviderFailure("providerUnavailable") from exc
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, ValidationError) as exc: raise InnovationProviderFailure("invalidResponse") from exc
