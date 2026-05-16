"""Chinese predicted-label tokens mapped to English display equivalents (for en-only UI paths)."""

from __future__ import annotations

from typing import Dict, Final

PREDICTED_LABEL_ZH_TO_EN: Final[Dict[str, str]] = {
    "阳性": "positive",
    "阴性": "negative",
    "高风险": "high risk",
    "低风险": "low risk",
    "死亡": "death",
    "生存": "survival",
}
