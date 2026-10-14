"""本机单人演示用肺结节 MCP 工具。默认由 Nexent 以 stdio 启动。"""

import os
import sys

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from audit import audit_settings, record_tool_event
from http_auth import BearerTokenASGI
from safe_workflow import run_case
from tool_client import ModelToolClient, ToolServiceError


mcp = FastMCP(
    "lung-nodule",
    instructions=(
        "仅接受已登记的病例 ID。检测结果和模型评分均为待复核候选，"
        "不得视为医生确认、最终诊断或已经校准的恶性概率。"
    ),
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*", "host.docker.internal:*"],
        allowed_origins=[
            "http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*",
            "http://host.docker.internal:*",
        ],
    ),
)


def _client() -> ModelToolClient:
    return ModelToolClient(
        os.getenv("MODEL_SERVER_URL", "http://127.0.0.1:8100"),
        os.getenv("MODEL_SERVER_TOKEN", ""),
    )


def _require_demo_case(case_id, tool, run_id=None):
    allowed = {item.strip() for item in os.getenv("MCP_ALLOWED_CASE_IDS", "").split(",") if item.strip()}
    if case_id not in allowed:
        record_tool_event(tool, case_id, "denied", run_id)
        return False
    return True


def _unavailable(code):
    messages = {
        "CASE_OUT_OF_SCOPE": "病例不在本次授权演示范围内；没有执行影像推理。",
        "CASE_NOT_REGISTERED": "病例未登记；没有执行影像推理，也没有可报告的结节结果。",
        "RUN_EXPIRED": "检测批次已失效；没有得到本次分类结果，请重新检测。",
        "INVALID_CANDIDATE_IDS": "候选编号无效；没有得到本次分类结果，请核对检测批次。",
        "MODEL_SERVICE_UNAVAILABLE": "模型服务不可用；没有得到影像结果，请检查服务并重试。",
    }
    return {"ok": False, "error_code": code, "message": messages.get(code, messages["MODEL_SERVICE_UNAVAILABLE"])}


@mcp.tool()
def detect_lung_nodules(case_id: str) -> dict:
    """按已登记病例 ID 检测。先检查返回的 ok；仅 ok=true 时可读取 run_id 和待复核候选。ok=false 表示无影像结论，必须停止。"""
    audit_settings()
    if not _require_demo_case(case_id, "detect_lung_nodules"):
        return _unavailable("CASE_OUT_OF_SCOPE")
    try:
        result = _client().detect(case_id)
    except ToolServiceError as exc:
        record_tool_event("detect_lung_nodules", case_id, "error")
        return _unavailable(exc.code)
    except Exception:
        record_tool_event("detect_lung_nodules", case_id, "error")
        raise
    record_tool_event("detect_lung_nodules", case_id, "success", result.get("run_id"))
    return {"ok": True, **result}


@mcp.tool()
def classify_nodules(case_id: str, run_id: str, candidate_ids: list[str]) -> dict:
    """对本次检测候选评分。先检查 ok；仅 ok=true 时可读取评分。ok=false 表示无分类结论；model_score 不是恶性概率。"""
    audit_settings()
    if not _require_demo_case(case_id, "classify_nodules", run_id):
        return _unavailable("CASE_OUT_OF_SCOPE")
    try:
        result = _client().classify(case_id, run_id, candidate_ids)
    except ToolServiceError as exc:
        record_tool_event("classify_nodules", case_id, "error", run_id)
        return _unavailable(exc.code)
    except Exception:
        record_tool_event("classify_nodules", case_id, "error", run_id)
        raise
    record_tool_event("classify_nodules", case_id, "success", run_id)
    return {"ok": True, **result}


@mcp.tool()
def analyze_case_candidates(case_id: str) -> dict:
    """按授权病例 ID 串行检测并分类，只返回可追溯的待复核候选或确定性错误说明。"""
    return run_case(case_id, detect_lung_nodules, classify_nodules)


if __name__ == "__main__":
    if "--http" in sys.argv:
        import uvicorn

        host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
        port = int(os.getenv("MCP_SERVER_PORT", "8200"))
        secure_app = BearerTokenASGI(mcp.streamable_http_app(), lambda: os.getenv("MCP_SERVER_TOKEN", ""))
        uvicorn.run(secure_app, host=host, port=port)
    else:
        mcp.run(transport="stdio")
