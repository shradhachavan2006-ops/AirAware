"""Trends endpoints.

GET /trends/series?cities=&start=&end=&metric=pm25_mean|station_count
    Returns per-city, per-date values for the chosen metric, plus a period
    summary table identical to the one produced in pages/2_Historical_Analysis.py.
    Missing values are returned as null (connectgaps=False equivalent).

GET /trends/download?cities=&start=&end=&metric=pm25_mean|station_count
    Returns the filtered data as a CSV file, mirroring the Streamlit download
    button behaviour in pages/2_Historical_Analysis.py.

Original Streamlit semantics preserved
----------------------------------------
* City filter: `df["city"].isin(selected)` — any subset of known cities.
* Date filter: `df["date"].between(pd.Timestamp(dates), pd.Timestamp(end_date))`.
* Metric choices: "pm25_mean" and "station_count" only.
* Summary table: observed_days, average, maximum — computed from non-NaN metric
  values only (Pandas default for .agg with count/mean/max).
* CSV download: the raw filtered `d` dataframe, all columns, index=False.
* connectgaps=False: NaN values for a metric are emitted as null in the series.
"""

from __future__ import annotations

import io
from typing import List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.data_loader import load_daily_data

router = APIRouter(prefix="/trends", tags=["Trends"])

ALLOWED_METRICS = {"pm25_mean", "station_count"}
METRIC_LABELS = {
    "pm25_mean": "PM2.5 (µg/m³)",
    "station_count": "Station count",
}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _parse_date(value: str, field: str) -> pd.Timestamp:
    try:
        return pd.Timestamp(value)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field} date: '{value}'. Expected YYYY-MM-DD.",
        )


def _safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        f = float(value)
        return None if np.isnan(f) else round(f, 4)
    except (TypeError, ValueError):
        return None


def _validate_and_filter(
    cities: List[str],
    start: Optional[str],
    end: Optional[str],
    metric: str,
) -> tuple[pd.DataFrame, pd.Timestamp | None, pd.Timestamp | None]:
    """Validate all parameters and return the filtered dataframe."""

    if metric not in ALLOWED_METRICS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"metric '{metric}' is not supported. "
                f"Choose from: {sorted(ALLOWED_METRICS)}."
            ),
        )

    start_ts: Optional[pd.Timestamp] = None
    end_ts: Optional[pd.Timestamp] = None
    if start is not None:
        start_ts = _parse_date(start, "start")
    if end is not None:
        end_ts = _parse_date(end, "end")
    if start_ts is not None and end_ts is not None and start_ts > end_ts:
        raise HTTPException(
            status_code=400,
            detail=f"start ({start}) must not be after end ({end}).",
        )

    df = load_daily_data()

    known_cities = sorted(df["city"].dropna().unique().tolist())

    # Validate individual city names
    unknown = [c for c in cities if c not in known_cities]
    if unknown:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown cities: {unknown}. Known: {known_cities}.",
        )

    # Apply filters — mirrors: df[df["city"].isin(selected) & df["date"].between(...)]
    mask = df["city"].isin(cities)
    if start_ts is not None and end_ts is not None:
        mask &= df["date"].between(start_ts, end_ts)
    elif start_ts is not None:
        mask &= df["date"] >= start_ts
    elif end_ts is not None:
        mask &= df["date"] <= end_ts

    filtered = df[mask].copy()
    return filtered, start_ts, end_ts


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/series")
def get_trends_series(
    cities: List[str] = Query(
        ...,
        description="One or more city names. Repeat the parameter for multiple cities.",
    ),
    start: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD."),
    end: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD."),
    metric: str = Query(
        "pm25_mean",
        description="Metric to return: 'pm25_mean' or 'station_count'.",
    ),
):
    """Return per-city time series values for the chosen metric.

    Each item in ``series`` is:
      { "city": str, "data": [{"date": "YYYY-MM-DD", "<metric>": float|null}, ...] }

    Null values preserve the missing-date gap (connectgaps=False equivalent).
    The ``summary`` array mirrors the period summary table from Historical Analysis.
    """
    filtered, start_ts, end_ts = _validate_and_filter(cities, start, end, metric)

    # --- Time series per city ------------------------------------------------
    series: list[dict] = []
    for city in cities:
        city_df = filtered[filtered["city"] == city].sort_values("date")
        data = [
            {
                "date": row["date"].strftime("%Y-%m-%d"),
                metric: _safe_float(row[metric]) if metric != "station_count"
                else (int(row[metric]) if pd.notna(row.get(metric)) else None),
            }
            for _, row in city_df.iterrows()
        ]
        series.append({"city": city, "data": data})

    # --- Summary table -------------------------------------------------------
    # Mirrors: summary = d.groupby("city").agg(
    #     observed_days=(metric, "count"),
    #     average=(metric, "mean"),
    #     maximum=(metric, "max")
    # )
    summary: list[dict] = []
    if not filtered.empty and metric in filtered.columns:
        grp = (
            filtered.groupby("city", as_index=False)
            .agg(
                observed_days=(metric, "count"),
                average=(metric, "mean"),
                maximum=(metric, "max"),
            )
        )
        for _, row in grp.iterrows():
            summary.append(
                {
                    "city": str(row["city"]),
                    "observed_days": int(row["observed_days"]),
                    "average": _safe_float(row["average"]),
                    "maximum": _safe_float(row["maximum"]),
                }
            )

    return {
        "filters": {
            "cities": cities,
            "start": start_ts.strftime("%Y-%m-%d") if start_ts else None,
            "end": end_ts.strftime("%Y-%m-%d") if end_ts else None,
            "metric": metric,
            "metric_label": METRIC_LABELS[metric],
        },
        "series": series,
        "summary": summary,
    }


@router.get("/download")
def get_trends_download(
    cities: List[str] = Query(..., description="City names to include."),
    start: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD."),
    end: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD."),
    metric: str = Query(
        "pm25_mean",
        description="Metric being viewed: 'pm25_mean' or 'station_count'. "
        "Does not filter columns; all columns are exported.",
    ),
):
    """Download the filtered dataset as a CSV file.

    Mirrors the Streamlit download button:
        st.download_button(..., d.to_csv(index=False), ...)
    All dataset columns are included, not just the selected metric.
    """
    filtered, _, _ = _validate_and_filter(cities, start, end, metric)

    # Serialize date column for CSV
    out = filtered.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    csv_bytes = out.to_csv(index=False).encode("utf-8")

    filename = "airaware_filtered_history.csv"
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
