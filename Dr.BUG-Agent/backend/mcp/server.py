"""
Read-only workbench context MCP, separate from executable ClinicalWorkbenchMCP tools (mcp_facade).

Currently registers contracted tools; in-process execution calls core implementations directly through backend.agent.mcp_adapter.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from fastmcp import FastMCP  # type: ignore
except Exception:  # pragma: no cover - consistent with mcp_facade

    class FastMCP:  # type: ignore[override]
        def __init__(self, name: str):
            self.name = name

        def tool(self):
            def decorator(func):
                return func

            return decorator


from backend.mcp.tools.context_tools import build_current_context_snapshot_from_bundle
from backend.mcp.tools.training_tools import build_latest_training_summary_mcp_result

workbench_context_mcp = FastMCP("WorkbenchContextMCP")


@workbench_context_mcp.tool()
def get_current_context(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Read-only: return the current workbench context summary. The bundle is injected by mcp_adapter and may include chat_context, tasks_meta, pending summaries, and related metadata.
    """
    if not isinstance(bundle, dict):
        bundle = {}
    return build_current_context_snapshot_from_bundle(bundle)


@workbench_context_mcp.tool()
def get_latest_training_summary(bundle: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Read-only: latest training task summary. In-process calls inject a snapshot or call core functions through the adapter; without a bundle, fall back to runtime.task_repo.
    """
    b = bundle if isinstance(bundle, dict) else {}
    snap = b.get("snapshot")
    if isinstance(snap, dict) and b.get("snapshot_version") == 1:
        return dict(snap)
    from backend import runtime

    return build_latest_training_summary_mcp_result(runtime.task_repo)
