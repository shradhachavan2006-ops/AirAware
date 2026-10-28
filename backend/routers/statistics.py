"""Statistics overview endpoint.

GET /statistics/overview

Returns the city-level descriptive statistics used by pages/3_Statistical_Insights.py:
- City summary: mean, median, sample std (ddof=1), maximum, valid-day count.
- Box-plot data: quartiles (Q1, Q2/median, Q3) and outlier points per city
  using the same method as plotly express px.box (IQR fences = Q1-1.5*IQR,
  Q3+1.5*IQR).
- Data coverage table: first/last date, total rows, valid PM2.5 days,
  missing PM2.5 rows, average station count — per city.
- Summary KPI highlights: highest-average city, most-variable city,
  total valid measurements.

Original Streamlit semantics preserved
----------------------------------------
* `valid = df.dropna(subset=["pm25_mean"])` — all calculations use only
  non-NaN pm25_mean rows.
* `std` uses pandas default ddof=1 (sample std).
* Box-plot outliers: Plotly's `points="outliers"` shows values outside
  [Q1 - 1.5*IQR, Q3 + 1.5*IQR]. We compute these explicitly so the
  frontend can render them without reimplementing the rule.
* Coverage table uses the full `df` (not `valid`) for total row counts,
  matching:
    df.groupby("city").agg(
        first_date=("date","min"), last_date=("date","max"),
        available_rows=("date","count"), valid_pm25_days=("pm25_mean","count"),
        avg_station_count=("station_count","mean")
    )
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException

from backend.data_loader import load_daily_data

router = APIRouter(prefix="/statistics", tags=["Statistics"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        f = float(value)
        return None if np.isnan(f) else round(f, 4)
    except (TypeError, ValueError):
        return None


def _boxplot_stats(series: pd.Series) -> dict:
    """Compute Plotly-compatible box-plot stats for a numeric series.

    Returns Q1, median (Q2), Q3, lower fence, upper fence, and outlier values.
    Outliers are values outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR].
    """
    clean = series.dropna()
    if clean.empty:
        return {
            "q1": None, "median": None, "q3": None,
            "lower_fence": None, "upper_fence": None,
            "outliers": [],
        }
    q1 = float(clean.quantile(0.25))
    median = float(clean.quantile(0.50))
    q3 = float(clean.quantile(0.75))
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    outliers = sorted(clean[(clean < lower_fence) | (clean > upper_fence)].tolist())
    return {
        "q1": round(q1, 4),
        "median": round(median, 4),
        "q3": round(q3, 4),
        "lower_fence": round(lower_fence, 4),
        "upper_fence": round(upper_fence, 4),
        "min_non_outlier": round(float(clean[clean >= lower_fence].min()), 4) if not clean[clean >= lower_fence].empty else round(q1, 4),
        "max_non_outlier": round(float(clean[clean <= upper_fence].max()), 4) if not clean[clean <= upper_fence].empty else round(q3, 4),
        "outliers": [round(v, 4) for v in outliers],
    }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/overview")
def get_statistics_overview():
    """Return descriptive statistics for all cities, using the full dataset.

    Mirrors pages/3_Statistical_Insights.py exactly.
    """
    df = load_daily_data()

    # valid = df.dropna(subset=["pm25_mean"])
    valid = df.dropna(subset=["pm25_mean"]).copy()

    if valid.empty:
        raise HTTPException(
            status_code=503,
            detail="No valid PM2.5 values available in the dataset.",
        )

    # --- City summary --------------------------------------------------------
    # city_summary = valid.groupby("city").agg(
    #     mean=("pm25_mean","mean"), median=("pm25_mean","median"),
    #     std=("pm25_mean","std"), maximum=("pm25_mean","max"),
    #     days=("pm25_mean","count")
    # )
    city_grp = valid.groupby("city", as_index=False).agg(
        mean=("pm25_mean", "mean"),
        median=("pm25_mean", "median"),
        std=("pm25_mean", "std"),       # ddof=1 — pandas default
        maximum=("pm25_mean", "max"),
        days=("pm25_mean", "count"),
    )

    city_summary = []
    for _, row in city_grp.iterrows():
        city_summary.append(
            {
                "city": str(row["city"]),
                "mean": _safe_float(row["mean"]),
                "median": _safe_float(row["median"]),
                "std": _safe_float(row["std"]),
                "maximum": _safe_float(row["maximum"]),
                "valid_days": int(row["days"]),
            }
        )

    # --- Box-plot data -------------------------------------------------------
    boxplots = {}
    for city, group in valid.groupby("city"):
        boxplots[str(city)] = _boxplot_stats(group["pm25_mean"])

    # --- Coverage table ------------------------------------------------------
    # coverage = df.groupby("city").agg(
    #     first_date=("date","min"), last_date=("date","max"),
    #     available_rows=("date","count"), valid_pm25_days=("pm25_mean","count"),
    #     avg_station_count=("station_count","mean")
    # )
    cov_grp = df.groupby("city", as_index=False).agg(
        first_date=("date", "min"),
        last_date=("date", "max"),
        available_rows=("date", "count"),
        valid_pm25_days=("pm25_mean", "count"),
        avg_station_count=("station_count", "mean"),
    )

    coverage = []
    for _, row in cov_grp.iterrows():
        available = int(row["available_rows"])
        valid_days = int(row["valid_pm25_days"])
        coverage.append(
            {
                "city": str(row["city"]),
                "first_date": row["first_date"].strftime("%Y-%m-%d")
                if pd.notna(row["first_date"])
                else None,
                "last_date": row["last_date"].strftime("%Y-%m-%d")
                if pd.notna(row["last_date"])
                else None,
                "available_rows": available,
                "valid_pm25_days": valid_days,
                "missing_pm25_rows": available - valid_days,
                "avg_station_count": _safe_float(row["avg_station_count"]),
            }
        )

    # --- KPI highlights ------------------------------------------------------
    # most_variable = city_summary.sort_values("std", ascending=False).iloc[0]
    # highest = city_summary.sort_values("mean", ascending=False).iloc[0]
    sorted_by_mean = sorted(city_summary, key=lambda r: r["mean"] or 0, reverse=True)
    sorted_by_std = sorted(city_summary, key=lambda r: r["std"] or 0, reverse=True)
    highest = sorted_by_mean[0] if sorted_by_mean else None
    most_variable = sorted_by_std[0] if sorted_by_std else None

    return {
        "kpis": {
            "highest_avg_city": highest["city"] if highest else None,
            "highest_avg_pm25": highest["mean"] if highest else None,
            "most_variable_city": most_variable["city"] if most_variable else None,
            "most_variable_std": most_variable["std"] if most_variable else None,
            "total_valid_measurements": int(len(valid)),
        },
        "city_summary": city_summary,
        "boxplots": boxplots,
        "coverage": coverage,
    }
