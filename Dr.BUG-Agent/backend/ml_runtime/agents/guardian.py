"""Phase 3: Human-AI Negotiation (GuardianAgent)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GuardianAgent:
    """Manages doctor selection state and validates final feature set."""

    def __init__(self):
        self.selected_features: List[str] = []
        self.force_med_cols: bool = True
        self.med_cols: List[str] = []
        self.available_columns: List[str] = []
        self.recommended_sets: List[List[str]] = []
        self.importance_ranking: Dict[str, List[tuple]] = {}

    def set_context(
        self,
        recommended_sets: List[List[str]],
        importance_ranking: Dict[str, List[tuple]],
        med_cols: Optional[List[str]] = None,
        available_columns: Optional[List[str]] = None,
    ) -> None:
        """Set context for negotiation."""
        self.recommended_sets = recommended_sets
        self.importance_ranking = importance_ranking
        self.med_cols = med_cols or []
        self.available_columns = available_columns or []

    def set_selection(
        self,
        selected_features: List[str],
        force_med_cols: bool = True,
    ) -> None:
        """Set doctor's final feature selection."""
        self.selected_features = list(selected_features)
        self.force_med_cols = force_med_cols

    def get_final_features(self) -> List[str]:
        """Get final feature list (selected + optional med_cols). Only add med_cols that exist in data."""
        out = list(self.selected_features)
        avail = set(self.available_columns) if self.available_columns else None
        if self.force_med_cols and self.med_cols:
            for c in self.med_cols:
                if c not in out and (avail is None or c in avail):
                    out.append(c)
        return out

    def validate(self) -> tuple[bool, str]:
        """
        Validate selection. Returns (ok, message).
        """
        if not self.selected_features:
            return False, "Please select at least 1 feature"
        return True, "Validation passed"

    def get_selection_history(self) -> List[Dict[str, Any]]:
        """Return selection history for report (includes warnings)."""
        return getattr(self, '_selection_history', [
            {
                "selected": self.selected_features,
                "force_med_cols": self.force_med_cols,
                "med_cols": self.med_cols,
            }
        ])
    
    def add_history_entry(self, selected: List[str], warnings: List[Dict[str, Any]], ignored: bool = False) -> None:
        """Add a history entry with warnings."""
        if not hasattr(self, '_selection_history'):
            self._selection_history = []
        self._selection_history.append({
            "selected": selected,
            "force_med_cols": self.force_med_cols,
            "med_cols": self.med_cols,
            "warnings": warnings,
            "ignored": ignored,
            "timestamp": None  # Can be set by caller if needed
        })
