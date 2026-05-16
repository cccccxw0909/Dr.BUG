"""
Execute validated read-only tool plans using the existing read_only_tools handlers.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from backend.agent.tool_registry import is_registered_readonly_tool
from backend.tools.read_only_tools import ReadonlyToolContext, execute_readonly_tool


def run_readonly_plan(
    planned: List[Tuple[str, Dict[str, Any]]],
    ctx: ReadonlyToolContext,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Run each (tool_name, arguments) in order.

    Returns (tool_names, tool_result_bundles) where each bundle matches execute_readonly_tool:
    {"ok": bool, "tool": str, "result": ...} or {"ok": False, "error": ..., "tool": name}.
    """
    tool_names: List[str] = []
    tool_results: List[Dict[str, Any]] = []
    for name, args in planned:
        n = str(name)
        tool_names.append(n)
        if not is_registered_readonly_tool(n):
            tool_results.append({"ok": False, "error": "unregistered_readonly_tool", "tool": n})
            continue
        tool_results.append(execute_readonly_tool(n, dict(args or {}), ctx))
    return tool_names, tool_results
