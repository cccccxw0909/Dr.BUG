"""Chinese follow-up action labels mapped to English tokens for English semantic key_points."""

from __future__ import annotations

from typing import Dict, Final

FOLLOWUP_ACTION_LABEL_ZH_TO_EN: Final[Dict[str, str]] = {
    "查看排序结果": "view_ranked_results",
    "查看候选方案排序": "view_ranked_regimens",
}
