"""关键病例流程由工具证据决定，不由语言模型解释错误。"""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from safe_workflow import run_case  # noqa: E402


def test_unregistered_case_stops_after_real_detect_error():
    calls = []

    def detect(case_id):
        calls.append(("detect", case_id))
        return {"ok": False, "error_code": "CASE_NOT_REGISTERED", "message": "原始工具说明"}

    def classify(*args):
        calls.append(("classify", args))
        raise AssertionError("检测失败后不得分类")

    result = run_case("demo-001", detect, classify)

    assert calls == [("detect", "demo-001")]
    assert result == {
        "ok": False,
        "case_id": "demo-001",
        "error_code": "CASE_NOT_REGISTERED",
        "summary": "病例未登记，未获得影像结果。请核对授权病例清单后重试。",
        "review_status": "not_available",
    }


def test_success_uses_only_detected_candidate_ids_and_keeps_review_pending():
    calls = []

    def detect(case_id):
        calls.append(("detect", case_id))
        return {"ok": True, "case_id": case_id, "run_id": "run123", "findings": [
            {"candidate_id": "c001", "detection_score": 0.8, "review_status": "pending"},
        ]}

    def classify(case_id, run_id, candidate_ids):
        calls.append(("classify", case_id, run_id, candidate_ids))
        return {"ok": True, "case_id": case_id, "run_id": run_id, "findings": [
            {"candidate_id": "c001", "model_score": 0.4, "review_status": "pending"},
        ]}

    result = run_case("demo-001", detect, classify)

    assert calls == [("detect", "demo-001"), ("classify", "demo-001", "run123", ["c001"])]
    assert result["ok"] is True
    assert result["run_id"] == "run123"
    assert result["findings"] == [{"candidate_id": "c001", "model_score": 0.4, "review_status": "pending"}]
    assert result["review_status"] == "pending"
    assert "评分不是已校准的恶性概率" in result["summary"]


def test_mismatched_classification_result_fails_closed():
    detect = lambda case_id: {"ok": True, "case_id": case_id, "run_id": "run123", "findings": [
        {"candidate_id": "c001", "review_status": "pending"},
    ]}
    classify = lambda case_id, run_id, ids: {"ok": True, "case_id": case_id, "run_id": run_id, "findings": [
        {"candidate_id": "c999", "model_score": 0.99, "review_status": "pending"},
    ]}

    result = run_case("demo-001", detect, classify)

    assert result["ok"] is False
    assert result["error_code"] == "INVALID_TOOL_RESULT"
    assert result["review_status"] == "not_available"
    assert "findings" not in result


def test_out_of_scope_error_never_calls_classification():
    calls = []
    detect = lambda case_id: {"ok": False, "error_code": "CASE_OUT_OF_SCOPE"}

    def classify(*args):
        calls.append(args)

    result = run_case("demo-001", detect, classify)

    assert calls == []
    assert result["error_code"] == "CASE_OUT_OF_SCOPE"
    assert "未获得影像结果" in result["summary"]


def test_boolean_score_is_not_accepted_as_model_score():
    detect = lambda case_id: {"ok": True, "case_id": case_id, "run_id": "run123", "findings": [
        {"candidate_id": "c001", "review_status": "pending"},
    ]}
    classify = lambda case_id, run_id, ids: {"ok": True, "case_id": case_id, "run_id": run_id, "findings": [
        {"candidate_id": "c001", "model_score": True, "review_status": "pending"},
    ]}

    result = run_case("demo-001", detect, classify)

    assert result["error_code"] == "INVALID_TOOL_RESULT"
    assert "findings" not in result


def test_no_model_candidates_does_not_become_negative_diagnosis():
    calls = []
    detect = lambda case_id: {"ok": True, "case_id": case_id, "run_id": "run123", "findings": []}

    def classify(*args):
        calls.append(args)
        raise AssertionError("没有候选时不应分类")

    result = run_case("demo-001", detect, classify)

    assert calls == []
    assert result["ok"] is True
    assert result["findings"] == []
    assert result["review_status"] == "pending"
    assert "不能据此排除结节" in result["summary"]
