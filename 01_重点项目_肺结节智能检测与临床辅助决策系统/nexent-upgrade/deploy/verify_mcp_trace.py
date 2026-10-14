"""按脱敏病例 ID 验证一次 MCP 工具执行的签名审计事件。"""

import argparse
import os
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp-server"))
from audit import matching_events  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--tool", choices=["detect_lung_nodules", "classify_nodules"], required=True)
    parser.add_argument("--since", type=float, required=True, help="测试前记录的 Unix 秒数")
    parser.add_argument("--outcome", choices=["success", "error", "denied"])
    args = parser.parse_args()

    path = os.getenv("MCP_AUDIT_LOG", "")
    key = os.getenv("MCP_AUDIT_KEY", "")
    if not path or not key:
        parser.error("需设置 MCP_AUDIT_LOG 和 MCP_AUDIT_KEY")
    events = matching_events(path, key, args.tool, args.case_id, args.since)
    if args.outcome:
        events = [entry for entry in events if entry["outcome"] == args.outcome]
    print(f"经签名验证的工具执行事件：{len(events)}")
    for entry in events:
        print(f"{entry['event_id']} {entry['tool']} {entry['outcome']} run_id={entry.get('run_id') or '-'}")
    if not events:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
