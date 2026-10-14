"""MCP 工具实际执行事件的最小签名审计；不记录原始病例 ID。"""

import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from uuid import uuid4


def audit_settings():
    path = os.getenv("MCP_AUDIT_LOG", "")
    key = os.getenv("MCP_AUDIT_KEY", "")
    if bool(path) != bool(key):
        raise RuntimeError("MCP 审计需要同时配置日志路径和密钥")
    return path, key


def _case_ref(key, case_id):
    return hmac.new(key.encode("utf-8"), str(case_id).encode("utf-8"), hashlib.sha256).hexdigest()


def _signature(key, entry):
    message = json.dumps(entry, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hmac.new(key.encode("utf-8"), message, hashlib.sha256).hexdigest()


def record_tool_event(tool, case_id, outcome, run_id=None):
    path, key = audit_settings()
    if not path:
        return
    entry = {
        "event_id": uuid4().hex,
        "at_epoch": time.time(),
        "tool": tool,
        "case_ref": _case_ref(key, case_id),
        "outcome": outcome,
        "run_id": run_id,
    }
    entry["signature"] = _signature(key, entry)
    encoded = (json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, encoded)
    finally:
        os.close(fd)


def verified_events(path, key, since):
    target = Path(path)
    if not target.exists():
        return []
    matches = []
    for line in target.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
            signature = entry.pop("signature")
            valid = hmac.compare_digest(signature, _signature(key, entry))
            if valid and entry.get("at_epoch", 0) >= since:
                matches.append(entry)
        except (ValueError, KeyError, TypeError):
            continue
    return matches


def matching_events(path, key, tool, case_id, since):
    expected_ref = _case_ref(key, case_id)
    return [
        entry for entry in verified_events(path, key, since)
        if entry.get("tool") == tool and entry.get("case_ref") == expected_ref
    ]
