from __future__ import annotations

import json
import httpx
from typing import Any, Protocol

from pydantic import ValidationError

from .contracts import DecisionRequirement
from .errors import DecisionError


class RequirementProvider(Protocol):
    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any] | str:
        ...


SYSTEM_PROMPT = """你是产品需求结构化解析器。只输出符合给定字段的 JSON，不输出解释。
识别产品类型、可量化属性、方向、单位、测量方法与仍需用户补充的必要约束。
不得虚构数值、阈值、测量方法、法规结论或企业数据；原文没有数值时 threshold 和
upperThreshold 必须为 null，并在 missingConstraints 中列出缺失项。
方向只能是 maximize、minimize、target 或 range。保留每项属性对应的 sourceText。
"""


class RequirementParser:
    def __init__(self, provider: RequirementProvider) -> None:
        self.provider = provider

    def parse(self, request_text: str) -> DecisionRequirement:
        if not request_text.strip():
            raise DecisionError("INCOMPLETE_CONSTRAINTS", "产品需求不能为空。")

        try:
            payload = self.provider.complete_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=request_text.strip(),
            )
            if isinstance(payload, str):
                payload = json.loads(payload)
            requirement = DecisionRequirement.model_validate(payload)
        except DecisionError:
            raise
        except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise DecisionError(
                "REQUIREMENT_SCHEMA_INVALID",
                "需求解析结果不符合结构化协议。",
                details={"reason": str(exc)},
            ) from exc
        except Exception as exc:
            raise DecisionError(
                "REQUIREMENT_PARSER_UNAVAILABLE",
                "需求理解服务暂时不可用。",
                retryable=True,
                details={"reason": type(exc).__name__},
            ) from exc

        self._reject_untraceable_numbers(requirement, request_text)
        return requirement

    @staticmethod
    def _reject_untraceable_numbers(
        requirement: DecisionRequirement, request_text: str
    ) -> None:
        for attribute in requirement.attributes:
            for field_name in ("threshold", "upperThreshold"):
                value = getattr(attribute, field_name)
                if value is None:
                    continue
                representations = {str(value), f"{value:g}"}
                if not any(token in request_text for token in representations):
                    raise DecisionError(
                        "REQUIREMENT_SCHEMA_INVALID",
                        "解析结果包含原始需求中不存在的数值。",
                        details={
                            "metric": attribute.metric,
                            "field": field_name,
                            "value": value,
                        },
                    )


class HttpRequirementProvider:
    def __init__(
        self,
        *,
        provider: str,
        model: str,
        base_url: str,
        api_key: str,
        enabled: bool,
        timeout: float = 45,
        client: httpx.Client | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.enabled = enabled
        self.timeout = timeout
        self.client = client or httpx.Client()

    def complete_json(
        self, *, system_prompt: str, user_prompt: str
    ) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("requirement provider is disabled")
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "request": user_prompt,
                        "schema": DecisionRequirement.model_json_schema(),
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        if self.provider == "ollama":
            response = self.client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0},
                    "messages": messages,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            content = response.json()["message"]["content"]
        else:
            headers = (
                {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
            )
            response = self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "temperature": 0,
                    "messages": messages,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
