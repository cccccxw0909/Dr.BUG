"""Locale pairs for backend.agent.reply_composer."""

from __future__ import annotations

from typing import Dict, Tuple

MESSAGES: Dict[str, Tuple[str, str]] = {
    "reply_composer.fallback_generic": (
        "当前可用信息有限。请查看任务面板状态或补全必要配置后再试。",
        "Current information is limited. Check the task panel status or complete the required configuration, then try again.",
    ),
}
