from __future__ import annotations

import argparse
import socket
import time
import os

from app.services.agent_command_service import agent_command_queue
from app.services.agent_command_worker import AgentCommandWorker
from app.services.agent_orchestrator import agent_orchestrator


def _capabilities() -> set[str]:
    return {item.strip() for item in os.getenv("AGENT_WORKER_CAPABILITIES", "cpu").split(",") if item.strip()}


def run_once_from_environment(wake_task_id: str | None = None) -> None:
    worker_id = os.getenv("AGENT_WORKER_ID", f"{socket.gethostname()}-agent-worker")
    worker = AgentCommandWorker(agent_command_queue, agent_orchestrator, worker_id, capabilities=_capabilities())
    worker.run_once()


def main() -> None:
    parser = argparse.ArgumentParser(description="菌藻启元智能体命令 worker")
    parser.add_argument("--worker-id", default=f"{socket.gethostname()}-agent-worker")
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--capabilities", default=os.getenv("AGENT_WORKER_CAPABILITIES", "cpu"))
    parser.add_argument("--max-concurrent", type=int, default=int(os.getenv("AGENT_WORKER_MAX_CONCURRENT", "1")))
    args = parser.parse_args()
    capabilities = {item.strip() for item in args.capabilities.split(",") if item.strip()}
    worker = AgentCommandWorker(agent_command_queue, agent_orchestrator, args.worker_id, capabilities=capabilities, max_concurrent=args.max_concurrent, labels={"host": socket.gethostname()})
    while True:
        task = worker.run_once()
        if args.once:
            return
        if task is None:
            time.sleep(max(0.1, min(args.poll_seconds, 10.0)))


if __name__ == "__main__":
    main()
