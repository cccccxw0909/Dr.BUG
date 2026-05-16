"""Time leakage detection."""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

LEAKAGE_PATTERNS = [
    r"after",
    r"post",
    r"future",
    r"post_",
    r"_after",
    r"_post",
    r"_future",
    r"outcome",
    r"label",
    r"target",
]


def detect_leakage(
    columns: List[str],
    index_time: Optional[str] = None,
    label_time: Optional[str] = None,
) -> Tuple[List[str], List[str]]:
    """
    Detect suspected leakage columns.

    Returns:
        suspected: List of column names that match leakage patterns.
        confirmed: List of columns explicitly confirmed as leakage (if index_time/label_time).
    """
    suspected: List[str] = []
    confirmed: List[str] = []

    for col in columns:
        col_lower = col.lower()
        for pat in LEAKAGE_PATTERNS:
            if re.search(pat, col_lower):
                suspected.append(col)
                break

    if index_time and index_time in columns:
        confirmed.append(index_time)
    if label_time and label_time in columns:
        confirmed.append(label_time)

    return list(dict.fromkeys(suspected)), list(dict.fromkeys(confirmed))


def get_leakage_report(
    suspected: List[str],
    confirmed: List[str],
    index_time: Optional[str] = None,
    label_time: Optional[str] = None,
) -> dict:
    """Build leakage report dict for JSON."""
    return {
        "suspected_columns": suspected,
        "confirmed_columns": confirmed,
        "index_time": index_time,
        "label_time": label_time,
        "requires_doctor_confirmation": len(suspected) > 0,
    }
