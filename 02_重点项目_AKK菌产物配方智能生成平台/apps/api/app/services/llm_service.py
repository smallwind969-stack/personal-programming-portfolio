from __future__ import annotations

import json
import os
from typing import Any

import httpx

from app.schemas.llm import LlmStatus


class LocalLlmService:
    def __init__(self) -> None:
        self.enabled = os.getenv("LOCAL_LLM_ENABLED", "true").lower() == "true"
        self.provider = os.getenv("LOCAL_LLM_PROVIDER", "ollama")
        self.base_url = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.model = os.getenv("LOCAL_LLM_MODEL", "qwen2.5:7b")
        self.timeout = float(os.getenv("LOCAL_LLM_TIMEOUT_SECONDS", "45"))

    def status(self) -> LlmStatus:
        available = False
        if self.enabled:
            try:
                url = f"{self.base_url}/api/tags" if self.provider == "ollama" else f"{self.base_url}/models"
                response = httpx.get(url, timeout=3)
                available = response.status_code < 500
            except httpx.HTTPError:
                available = False

        return LlmStatus(
            enabled=self.enabled,
            provider=self.provider,
            model=self.model,
            baseUrl=self.base_url,
            available=available,
            mode="local_llm_rag" if self.enabled else "rule_template",
        )

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
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            json={
                "model": self.model,
                "temperature": 0.18,
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
            "你是食品研发配方智能体，服务于 AKK 菌产物供应方和下游食品品牌的内部研发共创。"
            "你必须只输出一个合法 JSON 对象，不输出 Markdown、前后缀或思考过程。"
            "所有建议都必须标注为研发实验建议，不能描述为可直接上市的最终食品配方。"
            "你不能声称真实临床功效，不能替代法规审查和实验验证。"
            "你要基于给定知识库片段解释：为什么引用这份材料、它支持了什么性质判断、仍有哪些边界。"
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
                "task": "基于客户需求、AKK 原料、推荐配比和检索到的论文/法规知识片段，生成商品方案研发建议。",
                "output_schema": {
                    "productAdvantages": ["3-5 条面向下游客户的产品优势"],
                    "upgradeSuggestions": ["3-5 条后续升级建议，包含工艺、口感、稳定性或成本方向"],
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
                    "reasoningSummary": "解释为什么这样搭配 AKK 产物、辅料和目标商品形态",
                    "ratioReason": "解释当前配比为什么适合作为首轮小试起点",
                    "riskSummary": "核心风险、验证指标和不确定性边界",
                },
                "requirements": [
                    "所有内容使用中文。",
                    "引用知识片段时说明材料支持了什么判断，不要只堆论文标题。",
                    "必须包含安全性、稳定性、感官和法规边界提醒。",
                    "不能做疾病治疗、真实功效或上市可用性承诺。",
                    "输出必须是 JSON 对象。",
                ],
                "context": context,
            },
            ensure_ascii=False,
        )


local_llm_service = LocalLlmService()
