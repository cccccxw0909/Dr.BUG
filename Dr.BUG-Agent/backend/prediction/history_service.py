from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import TASK_DIR

HISTORY_DIR = TASK_DIR / "prediction_history"
RECORDS_DIR = HISTORY_DIR / "records"
INDEX_JSON = HISTORY_DIR / "index.json"


def _ensure_dirs() -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    if not INDEX_JSON.exists():
        INDEX_JSON.write_text("[]", encoding="utf-8")


def _read_index() -> List[Dict[str, Any]]:
    _ensure_dirs()
    try:
        rows = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
        if isinstance(rows, list):
            return [x for x in rows if isinstance(x, dict)]
    except Exception:
        pass
    return []


def _write_index(rows: List[Dict[str, Any]]) -> None:
    INDEX_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_record(record_id: str, payload: Dict[str, Any]) -> None:
    p = RECORDS_DIR / f"{record_id}.json"
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_single_summary(result: Dict[str, Any]) -> str:
    ptype = str(result.get("prediction_type") or "")
    if ptype == "classification":
        prob = result.get("predicted_probability")
        prob_txt = f"{float(prob):.4f}" if isinstance(prob, (float, int)) else "—"
        return f"Result: {result.get('outcome_display') or result.get('label_display') or '—'}; probability: {prob_txt}"
    v = result.get("predicted_value")
    return f"Predicted value: {v if v is not None else '—'}"


def archive_single_prediction(result: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_dirs()
    rid = f"pr_{uuid.uuid4().hex[:12]}"
    explanation = result.get("explanation") if isinstance(result.get("explanation"), dict) else {}
    rec = {
        "record_id": rid,
        "type": "single",
        "timestamp": result.get("timestamp"),
        "session_id": result.get("session_id"),
        "task_name": result.get("task_name") or "",
        "model_id": result.get("model_id") or "",
        "display_name": result.get("display_name") or result.get("model_id") or "",
        "predicted_label": result.get("predicted_label"),
        "predicted_value": result.get("predicted_value"),
        "predicted_probability": result.get("predicted_probability"),
        "summary_text": str(explanation.get("summary_text") or ""),
        "top_features": list(explanation.get("top_features") or []),
        "explanation_supported": bool(explanation.get("supported")),
        "waterfall_image_url": explanation.get("waterfall_image_url"),
        "force_image_url": explanation.get("force_image_url"),
        "input_summary": result.get("feature_values_used") or {},
        "warnings": list(result.get("warnings") or []),
        "result": result,
    }
    _write_record(rid, rec)
    idx = _read_index()
    idx.insert(
        0,
        {
            "record_id": rid,
            "type": "single",
            "timestamp": rec["timestamp"],
            "task_name": rec["task_name"],
            "model_id": rec["model_id"],
            "display_name": rec["display_name"],
            "summary": _build_single_summary(result),
        },
    )
    _write_index(idx)
    return rec


def archive_batch_prediction(result: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    _ensure_dirs()
    rid = f"pr_{uuid.uuid4().hex[:12]}"
    field_check = result.get("field_check") if isinstance(result.get("field_check"), dict) else {}
    rec = {
        "record_id": rid,
        "type": "batch",
        "timestamp": result.get("timestamp"),
        "session_id": session_id,
        "task_name": result.get("task_name") or "",
        "model_id": result.get("model_id") or "",
        "display_name": result.get("display_name") or result.get("model_id") or "",
        "file_name": result.get("file_name") or "",
        "total_rows": int(result.get("total_rows") or 0),
        "succeeded_rows": int(result.get("succeeded_rows") or 0),
        "failed_rows": int(result.get("failed_rows") or 0),
        "download_url": result.get("download_url") or "",
        "warnings": list(result.get("warnings") or []),
        "field_check_summary": {
            "matched_count": len(list(field_check.get("matched_fields") or [])),
            "missing_count": len(list(field_check.get("missing_fields") or [])),
            "extra_count": len(list(field_check.get("extra_fields") or [])),
            "required_missing_fields": list(field_check.get("required_missing_fields") or []),
        },
        "result": result,
    }
    _write_record(rid, rec)
    idx = _read_index()
    idx.insert(
        0,
        {
            "record_id": rid,
            "type": "batch",
            "timestamp": rec["timestamp"],
            "task_name": rec["task_name"],
            "model_id": rec["model_id"],
            "display_name": rec["display_name"],
            "summary": f"Total {rec['total_rows']}; succeeded {rec['succeeded_rows']}; failed {rec['failed_rows']}",
        },
    )
    _write_index(idx)
    return rec


def list_prediction_history(
    ptype: Optional[str] = None,
    task: Optional[str] = None,
    model: Optional[str] = None,
) -> List[Dict[str, Any]]:
    rows = _read_index()
    out: List[Dict[str, Any]] = []
    for r in rows:
        if ptype and str(r.get("type") or "") != ptype:
            continue
        if task and task not in str(r.get("task_name") or ""):
            continue
        if model and model not in str(r.get("model_id") or "") and model not in str(r.get("display_name") or ""):
            continue
        out.append(r)
    return out


def get_prediction_history_record(record_id: str) -> Optional[Dict[str, Any]]:
    _ensure_dirs()
    p = RECORDS_DIR / f"{record_id}.json"
    if not p.exists():
        return None
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None
