"""Dashboard summary endpoint.

GET /dashboard/summary?city=<city>&start=<YYYY-MM-DD>&end=<YYYY-MM-DD>

Returns all data required to render the Overview page:
- Selected city and period.
- Latest PM2.5 reading and its date (within the selected period).
- Average and peak PM2.5 for the period.
- Number of valid (non-NaN) city-days.
- 7-day rolling average series (window=7, min_periods=3) — connectgaps=False
  semantics are preserved by emitting null where the value is NaN.
- City-level summary (all cities in the period), sorted by descending
  average PM2.5.
- Up to 12 most-recent observations for the selected city.

Date filtering is inclusive on both ends.
PM2.5 values are reported in µg/m³, not as AQI.
Missing pm25_mean values are excluded from aggregate calculations but the
observation row is still returned in 'recent_observations' to preserve
coverage visibility.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from backend.data_loader import load_daily_data

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(value: str, field: str) -> pd.Timestamp:
    """Parse a YYYY-MM-DD string; raise 400 on failure."""
    try:
        return pd.Timestamp(value)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field} date: '{value}'. Expected YYYY-MM-DD.",
        )


def _safe_float(value) -> Optional[float]:
    """Return a Python float, or None if the value is NaN/None."""
    if value is None:
        return None
    try:
        f = float(value)
        return None if np.isnan(f) else round(f, 4)
    except (TypeError, ValueError):
        return None


def _serialize_row(row: pd.Series) -> dict:
    """Convert a single observation row to a JSON-serialisable dict."""
    date_val = row.get("date")
    return {
        "date": date_val.strftime("%Y-%m-%d") if pd.notna(date_val) else None,
        "city": str(row.get("city", "")),
        "pm25_mean": _safe_float(row.get("pm25_mean")),
        "station_count": (
            int(row["station_count"])
            if pd.notna(row.get("station_count"))
            else None
        ),
        "coverage_pct": _safe_float(row.get("coverage_pct")),
    }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/summary")
def get_dashboard_summary(
    city: str = Query(
        ...,
        description="City name (e.g. Pune). Must match a known city exactly.",
    ),
    start: str = Query(
        ...,
        description="Inclusive start date in YYYY-MM-DD format.",
    ),
    end: str = Query(
        ...,
        description="Inclusive end date in YYYY-MM-DD format.",
    ),
):
    """Return all data needed to render the Overview/Dashboard page.

    The response mirrors the semantics of the original Streamlit app.py:
    - `period_df` is the full dataset filtered to the date range across all cities.
    - `city_df` is `period_df` further filtered to the selected city, sorted by date.
    - Rolling average uses `rolling(7, min_periods=3).mean()` on `city_df`.
    - City snapshot aggregates from `all_valid` (= `period_df` with NaN pm25_mean dropped).
    - Recent observations are the last 12 rows of `city_df` (newest first), with all
      original columns, regardless of whether pm25_mean is present.
    """

    # --- Parse and validate query parameters --------------------------------
    start_ts = _parse_date(start, "start")
    end_ts = _parse_date(end, "end")

    if start_ts > end_ts:
        raise HTTPException(
            status_code=400,
            detail=(
                f"start ({start}) must not be after end ({end})."
            ),
        )

    df = load_daily_data()

    known_cities = sorted(df["city"].dropna().unique().tolist())
    if city not in known_cities:
        raise HTTPException(
            status_code=404,
            detail=(
                f"City '{city}' not found. "
                f"Known cities: {known_cities}."
            ),
        )

    # --- Apply date filter (inclusive) -------------------------------------
    # Mirrors: period_df = df[df["date"].between(start, end)].copy()
    period_df = df[df["date"].between(start_ts, end_ts)].copy()

    # city-specific slice, sorted by date (matches city_df in app.py)
    city_df = period_df[period_df["city"] == city].sort_values("date")

    # valid rows: pm25_mean is not NaN
    valid = city_df.dropna(subset=["pm25_mean"])          # matches `valid` in app.py
    all_valid = period_df.dropna(subset=["pm25_mean"])    # matches `all_valid` in app.py

    # --- Latest observation -------------------------------------------------
    # latest = valid.iloc[-1] if not valid.empty else None
    if not valid.empty:
        latest_row = valid.iloc[-1]
        latest_pm25 = _safe_float(latest_row["pm25_mean"])
        latest_date = latest_row["date"].strftime("%Y-%m-%d")
    else:
        latest_pm25 = None
        latest_date = None

    # --- KPI aggregates ----------------------------------------------------
    period_avg_pm25 = (
        _safe_float(valid["pm25_mean"].mean()) if not valid.empty else None
    )
    period_max_pm25 = (
        _safe_float(valid["pm25_mean"].max()) if not valid.empty else None
    )
    valid_city_days = int(len(valid))

    # --- 7-day rolling average series --------------------------------------
    # chart_df["7-day rolling mean"] = chart_df["pm25_mean"].rolling(7, min_periods=3).mean()
    # connectgaps=False is honoured by emitting null where the rolling value is NaN.
    rolling_series: list[dict] = []
    if not city_df.empty:
        chart_df = city_df.copy()
        chart_df["rolling_7d"] = (
            chart_df["pm25_mean"].rolling(7, min_periods=3).mean()
        )
        for _, r in chart_df.iterrows():
            rolling_series.append(
                {
                    "date": r["date"].strftime("%Y-%m-%d"),
                    "pm25_mean": _safe_float(r["pm25_mean"]),
                    "rolling_7d": _safe_float(r["rolling_7d"]),
                }
            )

    # --- City snapshot ------------------------------------------------------
    # city_summary = all_valid.groupby("city").agg(average_pm25=("pm25_mean","mean"),
    #                                               valid_days=("pm25_mean","count"))
    # sorted descending by average_pm25
    city_summary_rows: list[dict] = []
    if not all_valid.empty:
        city_summary = (
            all_valid.groupby("city", as_index=False)
            .agg(
                average_pm25=("pm25_mean", "mean"),
                valid_days=("pm25_mean", "count"),
            )
            .sort_values("average_pm25", ascending=False)
        )
        for _, r in city_summary.iterrows():
            city_summary_rows.append(
                {
                    "city": str(r["city"]),
                    "average_pm25": _safe_float(r["average_pm25"]),
                    "valid_days": int(r["valid_days"]),
                }
            )

    # --- Recent observations -----------------------------------------------
    # recent = city_df[display_cols].sort_values("date", ascending=False).head(12)
    recent_observations: list[dict] = []
    if not city_df.empty:
        recent = city_df.sort_values("date", ascending=False).head(12)
        for _, r in recent.iterrows():
            recent_observations.append(_serialize_row(r))

    # --- Build response -----------------------------------------------------
    return {
        "selected": {
            "city": city,
            "start": start_ts.strftime("%Y-%m-%d"),
            "end": end_ts.strftime("%Y-%m-%d"),
        },
        "kpis": {
            "latest_pm25": latest_pm25,
            "latest_date": latest_date,
            "period_avg_pm25": period_avg_pm25,
            "period_max_pm25": period_max_pm25,
            "valid_city_days": valid_city_days,
        },
        "trend_series": rolling_series,
        "city_summary": city_summary_rows,
        "recent_observations": recent_observations,
    }
