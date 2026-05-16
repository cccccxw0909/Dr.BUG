"""Chinese tokens rejected by narrative polish validation (forbidden / unsafe phrasing)."""

from __future__ import annotations

from typing import Final, Tuple

FORBIDDEN_ZH_TERMS: Final[Tuple[str, ...]] = (
    "因果",
    "证明",
    "证实",
    "处方",
    "临床更优",
    "显著优于",
    "最佳治疗",
    "患者行",
    "数据集id",
    "数据集ID",
    "任务id",
    "任务ID",
    "阶段",
)
