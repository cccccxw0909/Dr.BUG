"""Chinese tokens for prediction batch validation and binary-outcome semantics (metadata/label matching only)."""

from __future__ import annotations

from typing import Final, FrozenSet, Tuple

LEGAL_BINARY_CELL_VALUES: Final[FrozenSet[str]] = frozenset({"0", "1", "true", "false", "yes", "no", "是", "否"})

SURVIVAL_HINTS: Final[Tuple[str, ...]] = ("survival", "survive", "alive", "生存", "存活")
MORTALITY_HINTS: Final[Tuple[str, ...]] = ("mortality", "death", "die", "deceased", "死亡")

EFFICACYISH_TASK_NAME_MARKERS: Final[Tuple[str, ...]] = ("疗效", "临床", "efficacy", "outcome")

WINDOW_28D_TEXT_MARKERS: Final[Tuple[str, ...]] = ("28d", "28_day", "28-day", "28 day", "28天")
