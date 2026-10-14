"""空病例 Nexent 调试的独立验收门禁。"""

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "deploy"))
sys.path.insert(0, str(ROOT / "mcp-server"))

from audit import record_tool_event  # noqa: E402
from verify_agent_failure import check_failure_run  # noqa: E402


def test_refuses_self_validated_answer_without_real_tool_call(tmp_path):
    answer = "CASE_NOT_REGISTERED：未获得影像结果。"
    issues = check_failure_run(tmp_path / "missing.jsonl", "key", "demo-001", 0, answer)
    assert "缺少对应病例的真实检测工具事件" in issues


def test_accepts_one_signed_error_and_safe_failure_answer(tmp_path, monkeypatch):
    path = tmp_path / "events.jsonl"
    monkeypatch.setenv("MCP_AUDIT_LOG", str(path))
    monkeypatch.setenv("MCP_AUDIT_KEY", "key")
    record_tool_event("detect_lung_nodules", "demo-001", "error")
    assert check_failure_run(path, "key", "demo-001", 0, "CASE_NOT_REGISTERED：病例未登记，未获得影像结果。") == []


def test_refuses_hallucinated_second_case_even_when_first_call_was_real(tmp_path, monkeypatch):
    path = tmp_path / "events.jsonl"
    monkeypatch.setenv("MCP_AUDIT_LOG", str(path))
    monkeypatch.setenv("MCP_AUDIT_KEY", "key")
    record_tool_event("detect_lung_nodules", "demo-001", "error")
    record_tool_event("detect_lung_nodules", "case_123", "denied")
    issues = check_failure_run(path, "key", "demo-001", 0, "CASE_NOT_REGISTERED：未获得影像结果。")
    assert "工具事件不止一次；可能继续调用或切换病例" in issues


def test_refuses_false_negative_claim_after_real_error(tmp_path, monkeypatch):
    path = tmp_path / "events.jsonl"
    monkeypatch.setenv("MCP_AUDIT_LOG", str(path))
    monkeypatch.setenv("MCP_AUDIT_KEY", "key")
    record_tool_event("detect_lung_nodules", "demo-001", "error")
    issues = check_failure_run(path, "key", "demo-001", 0, "CASE_NOT_REGISTERED：未获得影像结果，未检出结节。")
    assert "回答包含无依据的影像或风险结论" in issues
