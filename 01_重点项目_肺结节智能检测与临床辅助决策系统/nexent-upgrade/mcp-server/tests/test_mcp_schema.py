"""用实际 MCP SDK 检查工具注册与 Nexent 可见的参数。"""

import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import mcp


def test_registered_tool_schemas_expose_only_ids():
    schemas = {tool.name: tool.parameters for tool in mcp._tool_manager.list_tools()}
    assert set(schemas) == {"detect_lung_nodules", "classify_nodules", "analyze_case_candidates"}
    assert set(schemas["detect_lung_nodules"]["properties"]) == {"case_id"}
    assert set(schemas["classify_nodules"]["properties"]) == {"case_id", "run_id", "candidate_ids"}
    assert set(schemas["analyze_case_candidates"]["properties"]) == {"case_id"}
