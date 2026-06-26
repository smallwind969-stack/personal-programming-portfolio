import json
import os
import socket
import urllib.error
import urllib.request


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_MODEL = "qwen3:8b"


def generate_with_local_qwen(prompt, timeout=45):
    """Call a local Ollama-hosted Qwen model. Returns (text, metadata)."""
    url = os.getenv("OLLAMA_URL", DEFAULT_OLLAMA_URL)
    model = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.8,
        },
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError, json.JSONDecodeError) as exc:
        return "", {
            "provider": "ollama",
            "model": model,
            "available": False,
            "error": str(exc),
        }

    return body.get("response", "").strip(), {
        "provider": "ollama",
        "model": model,
        "available": True,
    }
