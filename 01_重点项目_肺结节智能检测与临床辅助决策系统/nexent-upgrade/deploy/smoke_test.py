"""无患者数据的 HTTP MCP 联通与安全拒绝验收。

运行前设置 MCP_SERVER_URL、MCP_SERVER_TOKEN；MCP 进程的
MCP_ALLOWED_CASE_IDS 须包含 demo-001，目标模型服务须使用空病例清单。
"""

import asyncio
import json
import os

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


EXPECTED_TOOLS = {
    "detect_lung_nodules": {"case_id"},
    "classify_nodules": {"case_id", "run_id", "candidate_ids"},
    "analyze_case_candidates": {"case_id"},
}


def _result_dict(result):
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        return structured
    text = " ".join(item.text for item in result.content if item.type == "text")
    return json.loads(text)


async def main() -> None:
    url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8200/mcp")
    token = os.getenv("MCP_SERVER_TOKEN", "")
    if not token:
        raise SystemExit("MCP_SERVER_TOKEN 未配置")

    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, timeout=20
    ) as client:
        async with streamable_http_client(url, http_client=client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                actual = {
                    item.name: set(item.inputSchema.get("properties", {}))
                    for item in tools.tools
                }
                if actual != EXPECTED_TOOLS:
                    raise AssertionError(f"工具入参不符合受控契约：{actual}")
                print("MCP 握手和受控工具入参：通过")

                rejected = await session.call_tool(
                    "detect_lung_nodules", {"case_id": "demo-001"}
                )
                failure = _result_dict(rejected)
                if rejected.isError or failure.get("ok") is not False or failure.get("error_code") != "CASE_NOT_REGISTERED":
                    raise AssertionError("空病例清单未拒绝 demo-001")
                if "findings" in failure or "run_id" in failure:
                    raise AssertionError("未知病例错误结果混入了影像字段")
                print("空病例清单拒绝未登记病例：通过（结构化失败）")

                outside_scope = await session.call_tool(
                    "detect_lung_nodules", {"case_id": "case_123"}
                )
                blocked = _result_dict(outside_scope)
                if outside_scope.isError or blocked.get("ok") is not False or blocked.get("error_code") != "CASE_OUT_OF_SCOPE":
                    raise AssertionError("模型编造的其他病例未被 MCP 范围门禁拒绝")
                print("MCP 范围门禁拒绝其他病例：通过")

                reviewed = await session.call_tool("analyze_case_candidates", {"case_id": "demo-001"})
                reviewed_result = _result_dict(reviewed)
                if reviewed.isError or reviewed_result.get("error_code") != "CASE_NOT_REGISTERED":
                    raise AssertionError("单步病例流程没有保留真实未登记错误")
                if "未获得影像结果" not in reviewed_result.get("summary", "") or "findings" in reviewed_result:
                    raise AssertionError("单步病例流程没有安全停止")
                print("单步病例流程错误降级：通过")


if __name__ == "__main__":
    asyncio.run(main())
