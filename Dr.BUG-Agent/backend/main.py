from __future__ import annotations

import threading

import uvicorn

from backend.agent.orchestrator import registry as pending_action_registry
from backend.api.app import create_api_app
from backend.config import MCP_PORT, STATIC_PORT
from backend.tools.mcp_facade import REAL_FASTMCP_AVAILABLE, mcp
from backend.workers.task_executor import reconcile_unfinished_tasks


def run_http_api() -> None:
    app = create_api_app()
    uvicorn.run(app, host="0.0.0.0", port=STATIC_PORT, log_level="warning")


def run() -> None:
    reconcile_unfinished_tasks()
    pending_action_registry.reconcile_on_startup()
    if REAL_FASTMCP_AVAILABLE:
        threading.Thread(target=run_http_api, daemon=True).start()
        mcp.run(transport="sse", host="0.0.0.0", port=MCP_PORT)
    else:
        run_http_api()


if __name__ == "__main__":
    run()

