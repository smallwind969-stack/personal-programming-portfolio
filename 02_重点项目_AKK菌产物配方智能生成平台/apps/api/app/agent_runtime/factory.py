from __future__ import annotations

import importlib.util
import os

from app.agent_runtime.contracts import AgentRuntimeAdapter
from app.agent_runtime.deterministic import DeterministicRuntimeAdapter
from app.agent_runtime.sqlite_persistent import PersistentRuntimeAdapter, RuntimeCheckpointError


def langgraph_installed() -> bool:
    return importlib.util.find_spec("langgraph") is not None


def _create_langgraph_adapter(checkpoint_path: str | None = None) -> AgentRuntimeAdapter:
    from app.agent_runtime.langgraph_adapter import LangGraphRuntimeAdapter
    return LangGraphRuntimeAdapter(checkpoint_path=checkpoint_path)


def build_runtime_adapter() -> tuple[AgentRuntimeAdapter, str, str | None]:
    requested = os.getenv("AGENT_RUNTIME_BACKEND", "deterministic").strip().lower()
    checkpoint_path = os.getenv("AGENT_RUNTIME_CHECKPOINT_PATH", "").strip() or None
    if requested == "langgraph" and langgraph_installed():
        try:
            return _create_langgraph_adapter(checkpoint_path), "langgraph-sqlite" if checkpoint_path else "langgraph", None
        except (ImportError, RuntimeError, ValueError, RuntimeCheckpointError) as exc:
            return DeterministicRuntimeAdapter(), "deterministic", f"LangGraph initialization failed ({type(exc).__name__}); deterministic fallback is active"
    if requested == "langgraph":
        return DeterministicRuntimeAdapter(), "deterministic", "LangGraph dependency is unavailable; deterministic fallback is active"
    if requested != "deterministic":
        return DeterministicRuntimeAdapter(), "deterministic", f"Unknown runtime backend '{requested}'; deterministic fallback is active"
    if checkpoint_path:
        try:
            return PersistentRuntimeAdapter(checkpoint_path), "deterministic-sqlite", None
        except RuntimeCheckpointError as exc:
            return DeterministicRuntimeAdapter(), "deterministic", f"SQLite checkpoint initialization failed ({type(exc).__name__}); in-memory fallback is active"
    return DeterministicRuntimeAdapter(), "deterministic", None
