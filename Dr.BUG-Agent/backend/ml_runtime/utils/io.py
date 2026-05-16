"""Data I/O and artifact saving."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml

logger = logging.getLogger(__name__)

RANDOM_STATE = 42


def load_data(file_path: str | Path) -> pd.DataFrame:
    """Load CSV or XLSX file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            return pd.read_csv(path, encoding="utf-8-sig")
        if suffix in (".xlsx", ".xls"):
            return pd.read_excel(path)
        raise ValueError(f"Unsupported format: {suffix}. Use .csv or .xlsx")
    except Exception as e:
        logger.exception("Failed to load data: %s", e)
        raise


def compute_hash(data: bytes | str) -> str:
    """Compute SHA256 hash."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:8]


def get_run_dir(base: str | Path = "runs") -> Path:
    """Create timestamped run directory."""
    base = Path(base)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = base / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def save_artifact(
    run_dir: Path,
    name: str,
    obj: Any,
    *,
    config: Optional[Dict] = None,
) -> Path:
    """Save artifact (pickle, json, etc.) to run directory."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    out_path = run_dir / name
    if name.endswith(".json"):
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    elif name.endswith(".yaml") or name.endswith(".yml"):
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(obj, f, allow_unicode=True, default_flow_style=False)
    elif name.endswith(".csv"):
        obj.to_csv(out_path, index=False, encoding="utf-8-sig")
    elif name.endswith(".pkl") or name.endswith(".joblib"):
        import joblib

        joblib.dump(obj, out_path)
    else:
        raise ValueError(f"Unknown extension for: {name}")

    if config is not None:
        config_path = run_dir / "config.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, allow_unicode=True, default_flow_style=False)

    return out_path


def save_config(run_dir: Path, config: Dict[str, Any]) -> Path:
    """Save config.yaml to run directory."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "config.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, default_flow_style=False)
    return path


def load_config(run_dir: Path) -> Dict[str, Any]:
    """Load config from run directory."""
    path = Path(run_dir) / "config.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
