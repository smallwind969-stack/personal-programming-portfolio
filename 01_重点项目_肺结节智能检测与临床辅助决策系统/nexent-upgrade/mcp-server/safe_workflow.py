"""按真实工具结果推进的单病例演示流程。这里不调用语言模型。"""


ERROR_SUMMARIES = {
    "CASE_NOT_REGISTERED": "病例未登记，未获得影像结果。请核对授权病例清单后重试。",
    "CASE_OUT_OF_SCOPE": "病例不在本次授权范围内，未获得影像结果。",
    "MODEL_SERVICE_UNAVAILABLE": "模型服务不可用，未获得影像结果。请检查本机服务后重试。",
    "INVALID_TOOL_RESULT": "工具返回的数据不完整或不一致，未获得可信影像结果。",
    "RUN_EXPIRED": "检测批次已失效，未获得完整分类结果。请重新检测。",
    "INVALID_CANDIDATE_IDS": "候选编号无效，未获得完整分类结果。请重新检测。",
}


def _failure(case_id, code):
    safe_code = code if code in ERROR_SUMMARIES else "INVALID_TOOL_RESULT"
    return {
        "ok": False,
        "case_id": case_id,
        "error_code": safe_code,
        "summary": ERROR_SUMMARIES[safe_code],
        "review_status": "not_available",
    }


def _valid_identity(result, case_id, run_id=None):
    return (
        isinstance(result, dict)
        and result.get("ok") is True
        and result.get("case_id") == case_id
        and isinstance(result.get("run_id"), str)
        and bool(result["run_id"])
        and (run_id is None or result["run_id"] == run_id)
        and isinstance(result.get("findings"), list)
    )


def _candidate_ids(findings):
    ids = []
    for finding in findings:
        if not isinstance(finding, dict) or not isinstance(finding.get("candidate_id"), str) or not finding["candidate_id"]:
            return None
        ids.append(finding["candidate_id"])
    return ids if len(ids) == len(set(ids)) else None


def run_case(case_id, detect, classify):
    """执行检测→按本批候选分类；任何不一致都只返回不可用状态。"""
    try:
        detected = detect(case_id)
    except Exception:
        return _failure(case_id, "MODEL_SERVICE_UNAVAILABLE")
    if not isinstance(detected, dict):
        return _failure(case_id, "INVALID_TOOL_RESULT")
    if detected.get("ok") is False:
        return _failure(case_id, detected.get("error_code"))
    if not _valid_identity(detected, case_id):
        return _failure(case_id, "INVALID_TOOL_RESULT")
    ids = _candidate_ids(detected["findings"])
    if ids is None:
        return _failure(case_id, "INVALID_TOOL_RESULT")
    if not ids:
        return {
            "ok": True, "case_id": case_id, "run_id": detected["run_id"],
            "findings": [], "review_status": "pending",
            "summary": "模型未给出候选；仍需医生复核影像，不能据此排除结节。",
        }
    try:
        classified = classify(case_id, detected["run_id"], ids)
    except Exception:
        return _failure(case_id, "MODEL_SERVICE_UNAVAILABLE")
    if not isinstance(classified, dict):
        return _failure(case_id, "INVALID_TOOL_RESULT")
    if classified.get("ok") is False:
        return _failure(case_id, classified.get("error_code"))
    if not _valid_identity(classified, case_id, detected["run_id"]):
        return _failure(case_id, "INVALID_TOOL_RESULT")
    classified_ids = _candidate_ids(classified["findings"])
    if classified_ids is None or set(classified_ids) != set(ids):
        return _failure(case_id, "INVALID_TOOL_RESULT")
    findings = []
    for item in classified["findings"]:
        score = item.get("model_score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 1:
            return _failure(case_id, "INVALID_TOOL_RESULT")
        findings.append({"candidate_id": item["candidate_id"], "model_score": score, "review_status": "pending"})
    return {
        "ok": True, "case_id": case_id, "run_id": detected["run_id"],
        "findings": findings, "review_status": "pending",
        "summary": "仅获得模型候选与评分，均待医生复核；评分不是已校准的恶性概率。",
    }
