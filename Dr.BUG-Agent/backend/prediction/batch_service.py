from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import UploadFile

from backend.agent.chat_output_locale import is_english_output_locale
from backend.config import TASK_DIR
from backend.prediction.inference import run_single_sample
from backend.prediction.service import get_model_schema_bundle
from backend.prediction.zh_compat_tokens import LEGAL_BINARY_CELL_VALUES


def _read_batch_df(filename: str, content: bytes, locale: Optional[str] = None) -> pd.DataFrame:
    suffix = Path(filename or "").suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(BytesIO(content), encoding="utf-8-sig")
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(BytesIO(content))
    raise ValueError("Only csv/xlsx/xls files are supported")


def _schema_fields(
    model_id: str, locale: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    bundle = get_model_schema_bundle(model_id)
    if bundle is None:
        raise ValueError("Model not found or not registered")
    fields = list(bundle.get("fields") or [])
    order = list(bundle.get("feature_order") or [])
    if not order:
        raise ValueError("Model has no feature order configured")
    required = [str(f.get("name")) for f in fields if f.get("required") and f.get("name")]
    return fields, order, required


def _safe_cell(v: Any) -> Any:
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    return v


def _type_suspicious(
    df: pd.DataFrame, fields: List[Dict[str, Any]], locale: Optional[str] = None
) -> List[str]:
    warnings: List[str] = []
    for f in fields:
        name = str(f.get("name") or "")
        if not name or name not in df.columns:
            continue
        ftype = str(f.get("type") or "float")
        ser = df[name]
        non_na = ser.dropna()
        if non_na.empty:
            continue
        if ftype in ("float", "int") and not pd.api.types.is_numeric_dtype(non_na):
            warnings.append(f'Column "{name}" does not look numeric in the file')
            continue
        if ftype == "binary":
            vals = {str(x).strip().lower() for x in non_na.head(300).tolist()}
            legal = LEGAL_BINARY_CELL_VALUES
            if any(v not in legal for v in vals):
                warnings.append(f'Column "{name}" may not be binary; verify allowed values')
    return warnings


def check_batch_file(
    model_id: str, filename: str, content: bytes, ui_locale: Optional[str] = None
) -> Dict[str, Any]:
    fields, feature_order, required_fields = _schema_fields(model_id, ui_locale)
    df = _read_batch_df(filename, content, ui_locale)
    file_cols = [str(c) for c in df.columns.tolist()]
    col_set = set(file_cols)
    expected = set(feature_order)
    matched = [c for c in feature_order if c in col_set]
    missing = [c for c in feature_order if c not in col_set]
    extra = [c for c in file_cols if c not in expected]
    required_missing = [c for c in required_fields if c not in col_set]
    warnings = _type_suspicious(df, fields, ui_locale)
    return {
        "model_id": model_id,
        "file_name": filename,
        "total_columns": len(file_cols),
        "matched_fields": matched,
        "missing_fields": missing,
        "extra_fields": extra,
        "required_missing_fields": required_missing,
        "can_run": len(required_missing) == 0,
        "warnings": warnings,
    }


def run_batch_prediction(
    model_id: str, filename: str, content: bytes, ui_locale: Optional[str] = None
) -> Dict[str, Any]:
    fields, feature_order, _required_fields = _schema_fields(model_id, ui_locale)
    bundle = get_model_schema_bundle(model_id)
    display_name = str((bundle or {}).get("display_name") or model_id)
    check = check_batch_file(model_id, filename, content, ui_locale)
    if not check["can_run"]:
        raise ValueError("Missing required columns; cannot run batch prediction")

    df = _read_batch_df(filename, content, ui_locale)
    task_name = f"batch_{model_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir = TASK_DIR / "batch_predictions" / task_name
    out_dir.mkdir(parents=True, exist_ok=True)

    field_map = {str(f.get("name")): f for f in fields if f.get("name")}
    result_rows: List[Dict[str, Any]] = []
    failed = 0
    run_warnings: List[str] = []

    for idx, row in df.iterrows():
        raw_row: Dict[str, Any] = {str(c): _safe_cell(row[c]) for c in df.columns}
        values = {k: raw_row.get(k) for k in feature_order}
        for k in feature_order:
            f = field_map.get(k) or {}
            if not f.get("required") and values.get(k) is None:
                continue
        out_row = dict(raw_row)
        try:
            one = run_single_sample(
                model_id, values, session_id=None, include_explanation=False, ui_locale=ui_locale
            )
            out_row["prediction_label"] = one.get("predicted_label")
            out_row["prediction_value"] = one.get("predicted_value")
            out_row["prediction_probability"] = one.get("predicted_probability")
            warn_list = one.get("warnings") if isinstance(one.get("warnings"), list) else []
            out_row["warnings"] = " | ".join(str(x) for x in warn_list[:8]) if warn_list else ""
            if warn_list:
                run_warnings.append(f"Row {idx + 1}: missing or corrected inputs")
        except Exception as exc:
            failed += 1
            out_row["prediction_label"] = None
            out_row["prediction_value"] = None
            out_row["prediction_probability"] = None
            out_row["warnings"] = f"Prediction failed for row: {str(exc)}"
        result_rows.append(out_row)

    out_df = pd.DataFrame(result_rows)
    output_name = f"{task_name}_result.csv"
    output_path = out_dir / output_name
    out_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    total = int(len(out_df))
    succeeded = int(total - failed)
    ts = datetime.now(timezone.utc).isoformat()
    summary_text = f"Total {total} rows: succeeded {succeeded}, failed {int(failed)}."
    return {
        "model_id": model_id,
        "ui_locale": "en" if is_english_output_locale(ui_locale) else "zh",
        "display_name": display_name,
        "task_name": task_name,
        "file_name": filename,
        "total_rows": total,
        "succeeded_rows": succeeded,
        "failed_rows": int(failed),
        "download_url": f"/static/batch_predictions/{task_name}/{output_name}",
        "timestamp": ts,
        "warnings": list(dict.fromkeys(check.get("warnings", []) + run_warnings))[:20],
        "field_check": check,
        "summary_text": summary_text,
    }


async def read_upload_bytes(file: UploadFile) -> bytes:
    return await file.read()
