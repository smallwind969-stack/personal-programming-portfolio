from __future__ import annotations

import json
import os
from time import perf_counter
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from app.schemas.llm import LlmStatus, LlmUsageRoute


class LocalLlmService:
    def __init__(self) -> None:
        self.enabled = os.getenv("LOCAL_LLM_ENABLED", "true").lower() == "true"
        self.provider = os.getenv("LOCAL_LLM_PROVIDER", "ollama")
        self.base_url = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.api_key = os.getenv("LOCAL_LLM_API_KEY", "")
        self.model = os.getenv("LOCAL_LLM_MODEL", "qwen2.5:7b")
        self.timeout = float(os.getenv("LOCAL_LLM_TIMEOUT_SECONDS", "45"))

    def status(self) -> LlmStatus:
        available = False
        failure_category: str | None = "disabled" if not self.enabled else None
        latency_ms: int | None = None
        if self.enabled:
            started = perf_counter()
            try:
                if self.provider == "ollama":
                    response = httpx.get(f"{self.base_url}/api/tags", timeout=3)
                else:
                    headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
                    response = httpx.get(f"{self.base_url}/models", headers=headers, timeout=5)
                available = response.status_code < 400
                if not available:
                    failure_category = (
                        "authentication" if response.status_code in {401, 403} else
                        "endpoint_not_found" if response.status_code == 404 else
                        "upstream" if response.status_code >= 500 else "http_error"
                    )
            except httpx.TimeoutException:
                failure_category = "timeout"
            except httpx.HTTPError:
                failure_category = "connection"
                available = False
            finally:
                latency_ms = max(0, round((perf_counter() - started) * 1000))

        return LlmStatus(
            enabled=self.enabled,
            provider=self.provider,
            model=self.model,
            baseUrl=self._safe_base_url(),
            available=available,
            mode="llm_assisted" if available else "rule_fallback",
            apiKeyConfigured=bool(self.api_key),
            endpointScope=self._endpoint_scope(),
            latencyMs=latency_ms,
            failureCategory=failure_category,
            usageRoutes=self._usage_routes(),
            securityBoundaries=[
                "模型不执行数据清洗、单位换算或数学评估",
                "模型不晋升模型、参数或实验结果版本",
                "模型不生成或下发真实设备控制指令",
                "API 密钥只从服务端环境变量读取，不返回浏览器",
            ],
        )

    def _safe_base_url(self) -> str:
        parsed = urlsplit(self.base_url)
        hostname = parsed.hostname or ""
        if parsed.port:
            hostname = f"{hostname}:{parsed.port}"
        return urlunsplit((parsed.scheme, hostname, parsed.path.rstrip("/"), "", ""))

    def _endpoint_scope(self) -> str:
        host = (urlsplit(self.base_url).hostname or "").lower()
        return "local" if host in {"localhost", "127.0.0.1", "::1"} else "remote"

    @staticmethod
    def _usage_routes() -> list[LlmUsageRoute]:
        definitions = (
            ("schemaRecognition", "字段识别与定位", "SCHEMA_RECOGNITION_LLM_ENABLED", "解释字段语义与别名", "确定性字段规则"),
            ("resultInterpretation", "结果解释与建议", "RESULT_INTERPRETATION_LLM_ENABLED", "组织证据与研发解释", "证据模板"),
            ("productInnovation", "产品需求研判", "PRODUCT_INNOVATION_LLM_ENABLED", "把产品构想结构化为待验证需求", "规则安全回退"),
            ("featureBinding", "特征绑定顾问", "FEATURE_BINDING_LLM_ENABLED", "解释模型特征与设备字段候选", "标准字段别名"),
        )
        return [LlmUsageRoute(routeKey=key, label=label, enabled=os.getenv(env, "false").lower() == "true", role=role, fallback=fallback) for key, label, env, role, fallback in definitions]

    def enrich_formula(self, context: dict[str, Any]) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        prompt = self._build_prompt(context)
        try:
            content = self._call_ollama(prompt) if self.provider == "ollama" else self._call_openai_compatible(prompt)
            return self._parse_json(content)
        except (httpx.HTTPError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return None

    def _call_ollama(self, prompt: str) -> str:
        response = httpx.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.18, "num_predict": 1400},
                "messages": [
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    def _call_openai_compatible(self, prompt: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _system_prompt(self) -> str:
        return (
            "你是面向通用产业研发场景的实验数据解释与研发建议智能体，可服务食品、生物制造、菌藻培养及其他可配置产线。"
            "你必须只输出一个合法 JSON 对象，不输出 Markdown、解释前缀或思考过程。"
            "所有建议都必须标注为研发实验建议，不能描述为可直接生产、上市或用于设备控制的最终方案。"
            "你不能声称未经数据支持的真实性能或功效，不能替代法规、安全审查和现实实验验证。"
            "你要基于给定实验目标、数据资产、工艺假设、风险和知识库证据，解释证据关系以及下一轮应该验证什么。"
        )

    def _parse_json(self, content: str) -> dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()

        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end < start:
            raise ValueError("LLM response does not contain JSON")
        data = json.loads(text[start : end + 1])
        if not isinstance(data, dict):
            raise ValueError("LLM JSON must be an object")
        return data

    def _build_prompt(self, context: dict[str, Any]) -> str:
        return json.dumps(
            {
                "task": "基于客户需求、AKK 研发对象、推荐配比和知识库证据，生成内部研发建议书增强内容。",
                "output_schema": {
                    "productAdvantages": ["3-5 条面向内部研发或客户沟通的产品优势"],
                    "upgradeSuggestions": ["3-5 条后续升级建议，包含工艺、口感、稳定性、成本或验证方向"],
                    "companionIngredients": [
                        {
                            "ingredientId": "string",
                            "ingredientName": "string",
                            "category": "string",
                            "suggestedUsage": "string",
                            "purpose": "string",
                            "riskNote": "string",
                        }
                    ],
                    "reasoningSummary": "解释当前组合为什么适合作为首轮小试起点",
                    "riskSummary": "核心风险、验证指标和不确定性边界",
                },
                "requirements": [
                    "所有内容使用中文。",
                    "必须包含安全性、稳定性、感官和法规边界提醒。",
                    "不要做疾病治疗、真实功效或上市可用性承诺。",
                    "输出必须是 JSON 对象。",
                ],
                "context": context,
            },
            ensure_ascii=False,
        )


local_llm_service = LocalLlmService()
