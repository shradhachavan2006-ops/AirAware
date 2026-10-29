"""Dataset management endpoints.

GET  /datasets                  List all available datasets (demos + uploads)
POST /datasets/upload           Upload a CSV file
GET  /datasets/{id}             Dataset metadata
GET  /datasets/{id}/preview     First 25 rows as JSON
DELETE /datasets/{id}           Delete an uploaded dataset
"""

from __future__ import annotations

import io

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from backend.dataset_store import (
    DatasetInfo,
    delete_upload,
    get_df,
    get_info,
    list_datasets,
    register_upload,
)

router = APIRouter(prefix="/datasets", tags=["Datasets"])


def _info_dict(info: DatasetInfo) -> dict:
    return {
        "id": info.id,
        "name": info.name,
        "city_hint": info.city_hint,
        "is_demo": info.is_demo,
        "rows": info.rows,
        "total_rows": info.total_rows,
        "date_start": info.date_start,
        "date_end": info.date_end,
        "has_station_count": info.has_station_count,
        "has_coverage_pct": info.has_coverage_pct,
        "uploaded_at": info.uploaded_at,
        "warnings": info.warnings,
    }


@router.get("")
def list_all_datasets():
    """List all available datasets."""
    datasets = list_datasets()
    return {"datasets": [_info_dict(d) for d in datasets]}


@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(..., description="CSV file to upload"),
    name: str = Form("", description="Human-readable name for this dataset"),
):
    """Upload a CSV dataset and validate it.

    Required columns : date (YYYY-MM-DD), pm25_mean (float, µg/m³)
    Optional columns : station_count, coverage_pct, city

    Returns dataset metadata and a list of non-blocking warnings.
    On validation failure returns 422 with a human-readable error list.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are accepted. Ensure the file has a .csv extension.",
        )

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="File too large (max 10 MB).",
        )

    try:
        raw_df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot parse CSV: {exc}. "
                   "Ensure the file uses comma delimiters and UTF-8 encoding.",
        ) from exc

    display_name = (name.strip() or file.filename.removesuffix(".csv"))[:80]

    try:
        info, warnings = register_upload(raw_df, display_name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "dataset": _info_dict(info),
        "warnings": warnings,
        "message": (
            f"Dataset '{info.name}' uploaded successfully "
            f"({info.rows} valid rows, {info.date_start} to {info.date_end})."
        ),
    }


@router.get("/{dataset_id}")
def get_dataset_info(dataset_id: str):
    """Return metadata for a specific dataset."""
    try:
        info = get_info(dataset_id)
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _info_dict(info)


@router.get("/{dataset_id}/preview")
def get_dataset_preview(dataset_id: str, rows: int = 25):
    """Return the first N rows of a dataset as JSON."""
    if rows < 1 or rows > 200:
        raise HTTPException(status_code=400, detail="rows must be 1–200.")
    try:
        df = get_df(dataset_id)
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    preview_df = df.head(rows).copy()
    # Serialise dates as strings
    if "date" in preview_df.columns:
        preview_df["date"] = preview_df["date"].dt.strftime("%Y-%m-%d")

    records = preview_df.where(pd.notna(preview_df), None).to_dict(orient="records")
    return {
        "dataset_id": dataset_id,
        "columns": list(preview_df.columns),
        "rows": records,
        "total_rows": len(df),
        "showing": min(rows, len(df)),
    }


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: str):
    """Delete an uploaded dataset. Demo datasets cannot be deleted."""
    success = delete_upload(dataset_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset '{dataset_id}' not found or is a demo dataset (cannot be deleted).",
        )
    return {"message": f"Dataset '{dataset_id}' deleted."}
