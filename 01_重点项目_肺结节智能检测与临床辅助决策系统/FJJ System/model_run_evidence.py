"""从受控模型服务核验运行批次；仅供只读展示，不生成医生复核结论。"""

import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
RUN_ID_RE = re.compile(r"^[a-f0-9]{32}$|^[A-Za-z0-9_-]{6,64}$")


class EvidenceError(RuntimeError):
    pass


def fetch_verified_run(case_id, run_id, base_url, token):
    if not CASE_ID_RE.fullmatch(str(case_id)) or not RUN_ID_RE.fullmatch(str(run_id)):
        raise EvidenceError("病例 ID 或运行批次 ID 格式不正确")
    if not token or not base_url:
        raise EvidenceError("模型证据服务尚未配置")
    request = Request(
        f"{base_url.rstrip('/')}/runs/{case_id}/{run_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read(256 * 1024))
    except HTTPError as exc:
        if exc.code == 404:
            raise EvidenceError("未找到有效运行批次；请确认病例清单及服务是否重启") from None
        raise EvidenceError(f"模型证据服务请求失败（HTTP {exc.code}）") from None
    except (URLError, TimeoutError, ValueError, UnicodeError):
        raise EvidenceError("模型证据服务不可用或响应无效") from None

    if not isinstance(payload, dict) or payload.get("case_id") != case_id or payload.get("run_id") != run_id:
        raise EvidenceError("模型证据与当前病例或批次不匹配")
    findings = payload.get("findings")
    if not isinstance(findings, list) or len(findings) > 500:
        raise EvidenceError("模型证据中的候选列表无效")

    safe_findings = []
    seen = set()
    for item in findings:
        if not isinstance(item, dict) or item.get("review_status") != "pending":
            raise EvidenceError("模型证据包含无效的复核状态")
        candidate_id = item.get("candidate_id")
        if not isinstance(candidate_id, str) or not re.fullmatch(r"c[0-9]{3,5}", candidate_id) or candidate_id in seen:
            raise EvidenceError("模型证据中的候选 ID 无效或重复")
        seen.add(candidate_id)
        safe = {"candidate_id": candidate_id, "review_status": "pending"}
        for key in ("detection_score", "model_score"):
            if key in item:
                value = item[key]
                if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
                    raise EvidenceError("模型证据中的评分无效")
                safe[key] = value
        safe_findings.append(safe)
    return {"case_id": case_id, "run_id": run_id, "findings": safe_findings}
