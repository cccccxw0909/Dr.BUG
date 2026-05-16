from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from backend.api.request_locale import api_locale_prefers_english, resolve_api_user_locale_from_request
from backend.api.responses import error_response, success_response
from backend.config import TMP_UPLOAD_DIR
from backend.runtime import dataset_repo
from backend.schemas.api_response import (
    DatasetDetailSuccessResponse,
    DatasetListSuccessResponse,
    DatasetSchemaSuccessResponse,
    DatasetUploadSuccessResponse,
    ErrorResponse,
)
from backend.schemas.dataset import DatasetColumnInfo, DatasetMeta, DatasetSchemaInfo

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=DatasetListSuccessResponse, responses={404: {"model": ErrorResponse}})
async def list_datasets() -> Dict[str, Any]:
    datasets = [DatasetMeta.model_validate(item).model_dump(mode="json") for item in dataset_repo.list()]
    return success_response({"items": datasets, "total": len(datasets)})


@router.delete("/{dataset_id}", responses={404: {"model": ErrorResponse}})
async def delete_dataset(dataset_id: str, request: Request) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request)
    en = api_locale_prefers_english(loc)
    ok = dataset_repo.delete(dataset_id)
    if not ok:
        detail = (
            f"Dataset not found (dataset_id={dataset_id})." if en else f"dataset_id={dataset_id} not found"
        )
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "DATASET_NOT_FOUND"),
        )
    msg = "Dataset deleted." if en else "Dataset deleted."
    return success_response({"message": msg, "dataset_id": dataset_id})


@router.get("/{dataset_id}/file")
async def download_dataset_file(dataset_id: str, request: Request):
    """Serve the uploaded dataset file for local download (bounded preview remains on /preview)."""
    loc = resolve_api_user_locale_from_request(request)
    en = api_locale_prefers_english(loc)
    dataset = dataset_repo.get(dataset_id)
    if not dataset:
        detail = (
            f"Dataset not found (dataset_id={dataset_id})." if en else f"dataset_id={dataset_id} not found"
        )
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "DATASET_NOT_FOUND"),
        )
    file_path = Path(str(dataset.get("file_path", "")))
    if not file_path.exists():
        detail = (
            f"Dataset file not found (dataset_id={dataset_id})."
            if en
            else f"dataset_id={dataset_id} file not found"
        )
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "DATASET_FILE_NOT_FOUND"),
        )
    download_name = str(dataset.get("file_name") or file_path.name)
    return FileResponse(
        path=str(file_path),
        filename=download_name,
        media_type="application/octet-stream",
    )


@router.get("/{dataset_id}", response_model=DatasetDetailSuccessResponse, responses={404: {"model": ErrorResponse}})
async def get_dataset(dataset_id: str, request: Request) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request)
    en = api_locale_prefers_english(loc)
    dataset = dataset_repo.get(dataset_id)
    if not dataset:
        detail = (
            f"Dataset not found (dataset_id={dataset_id})." if en else f"dataset_id={dataset_id} not found"
        )
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "DATASET_NOT_FOUND"),
        )
    return success_response({"dataset": DatasetMeta.model_validate(dataset).model_dump(mode="json")})


@router.post("/upload", response_model=DatasetUploadSuccessResponse, responses={404: {"model": ErrorResponse}})
async def upload_dataset(
    request: Request,
    file: UploadFile = File(...),
    available_tasks: Optional[str] = Form(default=None),
) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request)
    en = api_locale_prefers_english(loc)
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xls"}:
        raise HTTPException(
            status_code=400,
            detail="Only csv/xlsx/xls files are supported." if en else "Only csv/xlsx/xls files are supported.",
        )

    tmp_path = TMP_UPLOAD_DIR / file.filename
    with tmp_path.open("wb") as fp:
        fp.write(await file.read())

    parsed_tasks: Optional[List[str]] = None
    raw_tasks = (available_tasks or "").strip()
    if raw_tasks:
        try:
            v = json.loads(raw_tasks)
            if isinstance(v, list):
                parsed_tasks = [str(x).strip() for x in v if str(x).strip()]
        except json.JSONDecodeError:
            parsed_tasks = [p.strip() for p in raw_tasks.split(",") if p.strip()]

    dataset = dataset_repo.create_from_uploaded_file(file.filename, tmp_path, parsed_tasks)
    tmp_path.unlink(missing_ok=True)
    return success_response({"dataset": dataset})


@router.get(
    "/{dataset_id}/schema",
    response_model=DatasetSchemaSuccessResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_dataset_schema(dataset_id: str, request: Request) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request)
    en = api_locale_prefers_english(loc)
    dataset = dataset_repo.get(dataset_id)
    if not dataset:
        detail = (
            f"Dataset not found (dataset_id={dataset_id})." if en else f"dataset_id={dataset_id} not found"
        )
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "DATASET_NOT_FOUND"),
        )
    file_path = Path(str(dataset.get("file_path", "")))
    if not file_path.exists():
        detail = (
            f"Dataset file not found (dataset_id={dataset_id})."
            if en
            else f"dataset_id={dataset_id} file not found"
        )
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "DATASET_FILE_NOT_FOUND"),
        )
    suffix = file_path.suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xls"}:
        detail = (
            "Only csv/xlsx/xls datasets support schema extraction."
            if en
            else "Only csv/xlsx/xls datasets support schema reading."
        )
        return JSONResponse(
            status_code=400,
            content=error_response(detail, "DATASET_FILE_TYPE_NOT_SUPPORTED"),
        )
    if suffix == ".csv":
        df = pd.read_csv(file_path, nrows=50, encoding="utf-8-sig")
    else:
        df = pd.read_excel(file_path, nrows=50)
    columns = [
        DatasetColumnInfo(
            name=str(col),
            dtype=str(df[col].dtype),
            is_numeric=bool(pd.api.types.is_numeric_dtype(df[col])),
        ).model_dump(mode="json")
        for col in df.columns
    ]
    return success_response({"schema": DatasetSchemaInfo(dataset_id=dataset_id, columns=columns).model_dump(mode="json")})


@router.get(
    "/{dataset_id}/preview",
    responses={404: {"model": ErrorResponse}},
)
async def get_dataset_preview(
    dataset_id: str,
    request: Request,
    target_column: Optional[str] = None,
    limit: int = 8,
    columns: Optional[str] = Query(
        default=None,
        description="Optional comma-separated column names to include in preview rows (order preserved).",
    ),
) -> Dict[str, Any]:
    loc = resolve_api_user_locale_from_request(request)
    en = api_locale_prefers_english(loc)
    dataset = dataset_repo.get(dataset_id)
    if not dataset:
        detail = (
            f"Dataset not found (dataset_id={dataset_id})." if en else f"dataset_id={dataset_id} not found"
        )
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "DATASET_NOT_FOUND"),
        )
    file_path = Path(str(dataset.get("file_path", "")))
    if not file_path.exists():
        detail = (
            f"Dataset file not found (dataset_id={dataset_id})."
            if en
            else f"dataset_id={dataset_id} file not found"
        )
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "DATASET_FILE_NOT_FOUND"),
        )
    suffix = file_path.suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xls"}:
        detail = (
            "Only csv/xlsx/xls datasets support preview." if en else "Only csv/xlsx/xls datasets support preview."
        )
        return JSONResponse(
            status_code=400,
            content=error_response(detail, "DATASET_FILE_TYPE_NOT_SUPPORTED"),
        )

    # Used only for chat-stage summary display; prioritize readability over complex analysis.
    if suffix == ".csv":
        df = pd.read_csv(file_path, encoding="utf-8-sig")
    else:
        df = pd.read_excel(file_path)

    n_rows = int(df.shape[0])
    n_cols_full = int(df.shape[1])

    subset_names: List[str] = []
    if columns and str(columns).strip():
        seen_subset: set[str] = set()
        for part in str(columns).split(","):
            name = part.strip()
            if not name or name in seen_subset:
                continue
            if name not in df.columns:
                continue
            seen_subset.add(name)
            subset_names.append(name)
        if subset_names:
            df = df.loc[:, subset_names]

    n_cols = int(df.shape[1])
    limit = max(1, min(int(limit), 10))

    missing_top = (
        df.isna()
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )
    missing_overview = [
        {"column": str(col), "missing_count": int(cnt)}
        for col, cnt in missing_top.items()
        if int(cnt) > 0
    ]

    numeric_cols = int(df.select_dtypes(include=["number"]).shape[1])
    categorical_cols = max(0, n_cols - numeric_cols)
    column_subset_applied = bool(subset_names)

    label_distribution: Dict[str, int] = {}
    tc = str(target_column or "").strip()
    if tc and tc in df.columns:
        try:
            vc = df[tc].value_counts(dropna=False).head(20)
            label_distribution = {str(k): int(v) for k, v in vc.items()}
        except Exception:
            label_distribution = {}

    preview_rows = df.head(limit).where(pd.notna(df), None).to_dict(orient="records")
    return success_response(
        {
            "preview": {
                "dataset_id": dataset_id,
                "row_count": n_rows,
                "column_count": n_cols,
                "full_column_count": n_cols_full,
                "column_subset_applied": column_subset_applied,
                "target_column": tc or None,
                "numeric_column_count": numeric_cols,
                "categorical_column_count": categorical_cols,
                "missing_overview": missing_overview,
                "label_distribution": label_distribution,
                "rows": preview_rows,
            }
        }
    )

