import json
from pathlib import Path
from unittest.mock import patch

import pytest

from audit import matching_events, verified_events
from tool_client import ToolServiceError
import server


def test_real_mcp_handler_error_writes_signed_event_without_case_id(tmp_path, monkeypatch):
    path = tmp_path / "tool-events.jsonl"
    monkeypatch.setenv("MCP_AUDIT_LOG", str(path))
    monkeypatch.setenv("MCP_AUDIT_KEY", "test-audit-key")
    monkeypatch.setenv("MCP_ALLOWED_CASE_IDS", "demo-001")

    class Client:
        def detect(self, case_id):
            raise ToolServiceError("模型服务请求失败（HTTP 404）", code="CASE_NOT_REGISTERED")

    with patch.object(server, "_client", return_value=Client()):
        result = server.detect_lung_nodules("demo-001")

    assert result == {
        "ok": False,
        "error_code": "CASE_NOT_REGISTERED",
        "message": "病例未登记；没有执行影像推理，也没有可报告的结节结果。",
    }
    assert "findings" not in result
    assert "run_id" not in result

    raw = path.read_text(encoding="utf-8")
    assert "demo-001" not in raw
    assert "test-audit-key" not in raw
    events = matching_events(path, "test-audit-key", "detect_lung_nodules", "demo-001", since=0)
    assert len(events) == 1
    assert events[0]["outcome"] == "error"


def test_signed_event_rejects_tampering(tmp_path, monkeypatch):
    path = tmp_path / "tool-events.jsonl"
    monkeypatch.setenv("MCP_AUDIT_LOG", str(path))
    monkeypatch.setenv("MCP_AUDIT_KEY", "test-audit-key")
    monkeypatch.setenv("MCP_ALLOWED_CASE_IDS", "demo-001")

    class Client:
        def detect(self, case_id):
            return {"case_id": case_id, "run_id": "run-123", "findings": []}

    with patch.object(server, "_client", return_value=Client()):
        server.detect_lung_nodules("demo-001")
    assert len(matching_events(path, "test-audit-key", "detect_lung_nodules", "demo-001", since=0)) == 1

    row = json.loads(path.read_text(encoding="utf-8"))
    row["outcome"] = "error"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert matching_events(path, "test-audit-key", "detect_lung_nodules", "demo-001", since=0) == []


def test_verified_events_exposes_all_valid_calls_without_raw_case_ids(tmp_path, monkeypatch):
    path = tmp_path / "tool-events.jsonl"
    monkeypatch.setenv("MCP_AUDIT_LOG", str(path))
    monkeypatch.setenv("MCP_AUDIT_KEY", "test-audit-key")
    server.record_tool_event("detect_lung_nodules", "demo-001", "error")
    server.record_tool_event("detect_lung_nodules", "invented-id", "denied")
    events = verified_events(path, "test-audit-key", since=0)
    assert [event["outcome"] for event in events] == ["error", "denied"]
    assert all("case_id" not in event for event in events)


def test_tool_rejects_case_outside_current_demo_scope_before_model_call(tmp_path, monkeypatch):
    path = tmp_path / "tool-events.jsonl"
    monkeypatch.setenv("MCP_AUDIT_LOG", str(path))
    monkeypatch.setenv("MCP_AUDIT_KEY", "test-audit-key")
    monkeypatch.setenv("MCP_ALLOWED_CASE_IDS", "demo-001")

    with patch.object(server, "_client", side_effect=AssertionError("model client must not run")) as client:
        result = server.detect_lung_nodules("case_123")
        client.assert_not_called()
    assert result["ok"] is False
    assert result["error_code"] == "CASE_OUT_OF_SCOPE"
    assert "findings" not in result
    events = matching_events(path, "test-audit-key", "detect_lung_nodules", "case_123", since=0)
    assert len(events) == 1
    assert events[0]["outcome"] == "denied"


def test_tool_fails_closed_without_demo_scope(monkeypatch):
    monkeypatch.delenv("MCP_ALLOWED_CASE_IDS", raising=False)
    monkeypatch.delenv("MCP_AUDIT_LOG", raising=False)
    monkeypatch.delenv("MCP_AUDIT_KEY", raising=False)
    with patch.object(server, "_client", side_effect=AssertionError("model client must not run")) as client:
        result = server.detect_lung_nodules("demo-001")
        client.assert_not_called()
    assert result["error_code"] == "CASE_OUT_OF_SCOPE"


def test_classification_cannot_switch_to_another_case(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_CASE_IDS", "demo-001")
    monkeypatch.delenv("MCP_AUDIT_LOG", raising=False)
    monkeypatch.delenv("MCP_AUDIT_KEY", raising=False)
    with patch.object(server, "_client", side_effect=AssertionError("model client must not run")) as client:
        result = server.classify_nodules("case_123", "run-1", ["c001"])
        client.assert_not_called()
    assert result["error_code"] == "CASE_OUT_OF_SCOPE"


def test_success_result_has_explicit_ok_marker(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_CASE_IDS", "demo-001")
    monkeypatch.delenv("MCP_AUDIT_LOG", raising=False)
    monkeypatch.delenv("MCP_AUDIT_KEY", raising=False)

    class Client:
        def detect(self, case_id):
            return {"case_id": case_id, "run_id": "run-123", "findings": []}

    with patch.object(server, "_client", return_value=Client()):
        result = server.detect_lung_nodules("demo-001")
    assert result["ok"] is True
    assert result["run_id"] == "run-123"


def test_expired_classification_run_has_no_scores(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_CASE_IDS", "demo-001")
    monkeypatch.delenv("MCP_AUDIT_LOG", raising=False)
    monkeypatch.delenv("MCP_AUDIT_KEY", raising=False)

    class Client:
        def classify(self, case_id, run_id, candidate_ids):
            raise ToolServiceError("模型服务请求失败（HTTP 409）", code="RUN_EXPIRED")

    with patch.object(server, "_client", return_value=Client()):
        result = server.classify_nodules("demo-001", "stale", ["c001"])
    assert result["ok"] is False
    assert result["error_code"] == "RUN_EXPIRED"
    assert "findings" not in result


def test_unexpected_error_is_not_relabelled_as_known_model_failure(tmp_path, monkeypatch):
    path = tmp_path / "tool-events.jsonl"
    monkeypatch.setenv("MCP_AUDIT_LOG", str(path))
    monkeypatch.setenv("MCP_AUDIT_KEY", "test-audit-key")
    monkeypatch.setenv("MCP_ALLOWED_CASE_IDS", "demo-001")

    class Client:
        def detect(self, case_id):
            raise AssertionError("unexpected failure")

    with patch.object(server, "_client", return_value=Client()):
        with pytest.raises(AssertionError, match="unexpected failure"):
            server.detect_lung_nodules("demo-001")
    events = matching_events(path, "test-audit-key", "detect_lung_nodules", "demo-001", since=0)
    assert len(events) == 1
    assert events[0]["outcome"] == "error"


def test_analyze_case_returns_canonical_error_and_one_signed_detect_event(tmp_path, monkeypatch):
    path = tmp_path / "tool-events.jsonl"
    monkeypatch.setenv("MCP_AUDIT_LOG", str(path))
    monkeypatch.setenv("MCP_AUDIT_KEY", "test-audit-key")
    monkeypatch.setenv("MCP_ALLOWED_CASE_IDS", "demo-001")

    class Client:
        def detect(self, case_id):
            raise ToolServiceError("HTTP 404", code="CASE_NOT_REGISTERED")

        def classify(self, *args):
            raise AssertionError("cannot classify after failed detect")

    with patch.object(server, "_client", return_value=Client()):
        result = server.analyze_case_candidates("demo-001")

    assert result["error_code"] == "CASE_NOT_REGISTERED"
    assert "未获得影像结果" in result["summary"]
    assert "findings" not in result
    events = verified_events(path, "test-audit-key", since=0)
    assert len(events) == 1
    assert events[0]["tool"] == "detect_lung_nodules"


def test_analyze_case_success_keeps_all_candidates_pending_and_audits_two_tools(tmp_path, monkeypatch):
    path = tmp_path / "tool-events.jsonl"
    monkeypatch.setenv("MCP_AUDIT_LOG", str(path))
    monkeypatch.setenv("MCP_AUDIT_KEY", "test-audit-key")
    monkeypatch.setenv("MCP_ALLOWED_CASE_IDS", "demo-001")

    class Client:
        def detect(self, case_id):
            return {"case_id": case_id, "run_id": "run123", "findings": [
                {"candidate_id": "c001", "review_status": "pending"},
            ]}

        def classify(self, case_id, run_id, candidate_ids):
            assert (case_id, run_id, candidate_ids) == ("demo-001", "run123", ["c001"])
            return {"case_id": case_id, "run_id": run_id, "findings": [
                {"candidate_id": "c001", "model_score": 0.5, "review_status": "pending"},
            ]}

    with patch.object(server, "_client", return_value=Client()):
        result = server.analyze_case_candidates("demo-001")

    assert result["ok"] is True
    assert result["review_status"] == "pending"
    assert result["findings"] == [{"candidate_id": "c001", "model_score": 0.5, "review_status": "pending"}]
    events = verified_events(path, "test-audit-key", since=0)
    assert [(event["tool"], event["outcome"]) for event in events] == [
        ("detect_lung_nodules", "success"), ("classify_nodules", "success"),
    ]
