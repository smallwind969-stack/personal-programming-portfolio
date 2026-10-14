import json
import os
import socket
import urllib.error
import urllib.request

try:
    import llm_api_config
except ImportError:
    llm_api_config = None


DEFAULT_API_BASE = "https://ai.rjyunk.com/v1"
DEFAULT_MODEL = "gpt-5.3-codex-spark"


class LLMClientError(RuntimeError):
    pass


def _env(name, default=""):
    return os.getenv(name, default).strip()


def _config(name, default=""):
    if llm_api_config is None:
        return default
    value = getattr(llm_api_config, name, default)
    return str(value).strip() if value is not None else default


def _api_key():
    return _env("LLM_API_KEY") or _env("OPENAI_API_KEY") or _config("API_KEY")


def _error_detail(exc):
    try:
        return exc.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def generate_with_llm_api(prompt, timeout=None):
    """Call an OpenAI-compatible chat completions API. Raises on any failure."""
    api_key = _api_key()
    if not api_key:
        raise LLMClientError("未配置大模型 API Key：请在 llm_api_config.py 中填写 API_KEY，或设置 LLM_API_KEY 环境变量。")

    api_base = (_env("LLM_API_BASE") or _config("API_BASE", DEFAULT_API_BASE)).rstrip("/")
    model = _env("LLM_MODEL") or _config("MODEL", DEFAULT_MODEL)
    timeout = timeout or int(_env("LLM_API_TIMEOUT") or _config("TIMEOUT", "60"))
    temperature = float(_env("LLM_TEMPERATURE") or _config("TEMPERATURE", "0.2"))

    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是肺结节 CT 医生复核工作台中的辅助 Agent。"
                    "必须基于输入的结构化信息生成谨慎、可审阅、面向医生的中文建议；"
                    "不得给出最终诊断，不得篡改结节坐标、概率、大小等关键数值。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base}/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "curl/8.0.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = _error_detail(exc)
        if exc.code == 403 and "1010" in detail:
            raise LLMClientError(
                "大模型 API 返回 HTTP 403 / 1010：接口网关拒绝了当前客户端请求。"
                "程序已加入 curl 风格请求头；如果仍失败，请确认 API Key、接口白名单或平台风控设置。"
            ) from exc
        raise LLMClientError(f"大模型 API 返回 HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError, json.JSONDecodeError) as exc:
        raise LLMClientError(f"大模型 API 调用失败: {exc}") from exc

    try:
        text = body["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise LLMClientError(f"大模型 API 返回格式异常: {body}") from exc

    if not text:
        raise LLMClientError("大模型 API 返回内容为空。")

    return text, {
        "provider": "openai_compatible_api",
        "api_base": api_base,
        "model": model,
        "available": True,
    }
