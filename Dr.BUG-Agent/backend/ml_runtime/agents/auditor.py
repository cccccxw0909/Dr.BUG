"""Phase 1: Data Audit (AuditorAgent)."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..utils.leakage import detect_leakage, get_leakage_report

logger = logging.getLogger(__name__)

# PII (Personally Identifiable Information) detection patterns (English column-name patterns)
SENSITIVE_PATTERNS = [
    "name", "patient_id", "id_card",
    "phone", "mobile", "tel",
    "email", "mail",
    "address", "addr",
    "birth", "birthday",
    "ssn", "social_security",
    "passport",
    "credit_card", "card_number"
]
# Match only when column name ends with _id or equals id, to avoid false positives like "Chronic Kidney Disease"
SENSITIVE_ID_PATTERNS = ("_id", "_id_", "id_card", "patient_id", "patientid", "case_id")


class AuditorAgent:
    """Data quality audit and cleaning."""

    def __init__(
        self,
        index_time: Optional[str] = None,
        label_time: Optional[str] = None,
        sensitive_cols: Optional[List[str]] = None,
        use_iqr_outlier: bool = True,
    ):
        self.index_time = index_time
        self.label_time = label_time
        self.sensitive_cols = sensitive_cols or []
        self.use_iqr_outlier = use_iqr_outlier

    def _infer_dtypes(self, df: pd.DataFrame) -> Dict[str, str]:
        """Infer column types."""
        result = {}
        for col in df.columns:
            s = df[col]
            if pd.api.types.is_numeric_dtype(s):
                if s.nunique() <= 2 and set(s.dropna().astype(int).unique()).issubset({0, 1}):
                    result[col] = "binary"
                else:
                    result[col] = "numeric"
            elif pd.api.types.is_datetime64_any_dtype(s):
                result[col] = "datetime"
            else:
                result[col] = "categorical"
        return result

    def _detect_sensitive_columns(self, columns: List[str]) -> List[str]:
        """
        Detect columns matching PII (Personally Identifiable Information) patterns.
        Uses rule-based keyword matching to identify potential PII columns.
        """
        found = []
        for col in columns:
            col_lower = col.lower().strip()
            # Check against PII patterns
            for pat in SENSITIVE_PATTERNS:
                if pat in col_lower:
                    found.append(col)
                    break
            else:
                # Check ID patterns (more strict matching)
                for pat in SENSITIVE_ID_PATTERNS:
                    if pat in col_lower or col_lower == "id":
                        found.append(col)
                        break
                # Additional check: exact match for common ID column names
                if col_lower in ["id", "patientid", "caseid", "subjectid"]:
                    if col not in found:
                        found.append(col)
        return list(dict.fromkeys(found))  # Remove duplicates while preserving order

    def _compute_missing_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Compute missing rate per column."""
        n = len(df)
        missing = df.isnull().sum()
        return {col: {"count": int(missing[col]), "rate": float(missing[col] / n) if n > 0 else 0} for col in df.columns}

    def _detect_constant_columns(self, df: pd.DataFrame) -> List[str]:
        """Detect constant columns."""
        return [c for c in df.columns if df[c].nunique(dropna=True) <= 1]

    def _detect_duplicate_columns(self, df: pd.DataFrame) -> List[str]:
        """Detect duplicate columns (same values)."""
        dupes = []
        cols = list(df.columns)
        for i, c1 in enumerate(cols):
            for c2 in cols[i + 1 :]:
                if df[c1].equals(df[c2]):
                    dupes.append(c2)
        return list(dict.fromkeys(dupes))

    def _detect_outliers_iqr(self, df: pd.DataFrame) -> Dict[str, Dict[str, int]]:
        """Detect outliers using IQR for numeric columns."""
        result = {}
        for col in df.select_dtypes(include=[np.number]).columns:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue
            low = q1 - 1.5 * iqr
            high = q3 + 1.5 * iqr
            n_low = (df[col] < low).sum()
            n_high = (df[col] > high).sum()
            if n_low > 0 or n_high > 0:
                result[col] = {"below": int(n_low), "above": int(n_high)}
        return result

    def run(
        self,
        df: pd.DataFrame,
        drop_sensitive: bool = True,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Run full audit.

        Returns:
            clean_df: Cleaned dataframe.
            data_quality_report: JSON-serializable report.
        """
        df = df.copy()
        dtypes = self._infer_dtypes(df)

        sensitive_detected = self._detect_sensitive_columns(list(df.columns))
        cols_to_drop = list(self.sensitive_cols) if self.sensitive_cols else []
        if drop_sensitive:
            cols_to_drop = list(dict.fromkeys(cols_to_drop + sensitive_detected))
        cols_to_drop = [c for c in cols_to_drop if c in df.columns]
        if cols_to_drop:
            df = df.drop(columns=cols_to_drop)

        missing_stats = self._compute_missing_stats(df)
        constant_cols = self._detect_constant_columns(df)
        duplicate_cols = self._detect_duplicate_columns(df)
        outlier_stats = self._detect_outliers_iqr(df) if self.use_iqr_outlier else {}

        suspected, confirmed = detect_leakage(list(df.columns), self.index_time, self.label_time)
        leakage_report = get_leakage_report(suspected, confirmed, self.index_time, self.label_time)

        missing_summary = {k: v["rate"] for k, v in missing_stats.items() if v["rate"] > 0}

        report = {
            "n_rows": int(len(df)),
            "n_cols": int(len(df.columns)),
            "dtypes": dtypes,
            "missing_stats": missing_stats,
            "missing_summary": missing_summary,
            "constant_columns": constant_cols,
            "duplicate_columns": duplicate_cols,
            "outlier_stats": outlier_stats,
            "sensitive_removed": cols_to_drop,
            "sensitive_detected": sensitive_detected,
            "leakage": leakage_report,
        }

        return df, report
