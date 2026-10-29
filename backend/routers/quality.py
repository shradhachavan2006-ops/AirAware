"""Data quality profiling endpoints.

GET /quality/{dataset_id}
    Full data quality profile: shape, column statistics, date gaps,
    duplicate dates, outlier detection, and an overall quality score.

GET /quality/{dataset_id}/cleaned
    Returns the cleaned version of the dataset as a downloadable CSV.
"""

from __future__ import annotations

import io
from datetime import timedelta

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.dataset_store import get_df, get_info

router = APIRouter(prefix="/quality", tags=["Data Quality"])


def _outlier_indices(series: pd.Series) -> pd.Index:
    """Return index positions where values are outside the IQR fences."""
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return series[(series < lo) | (series > hi)].index


def _date_gaps(series: pd.Series, threshold_days: int = 3) -> list[dict]:
    """Detect calendar gaps in a sorted date Series.

    Returns gaps where consecutive observations are more than
    ``threshold_days`` apart.
    """
    dates = pd.to_datetime(series.dropna()).sort_values()
    gaps: list[dict] = []
    for i in range(1, len(dates)):
        delta = (dates.iloc[i] - dates.iloc[i - 1]).days
        if delta > threshold_days:
            gaps.append({
                "gap_start": dates.iloc[i - 1].strftime("%Y-%m-%d"),
                "gap_end":   dates.iloc[i].strftime("%Y-%m-%d"),
                "missing_days": delta - 1,
            })
    return gaps


def _column_profile(df: pd.DataFrame, col: str) -> dict:
    s = df[col]
    base = {
        "name": col,
        "dtype": str(s.dtype),
        "total": len(s),
        "null_count": int(s.isna().sum()),
        "null_pct": round(s.isna().mean() * 100, 2),
        "unique_count": int(s.nunique(dropna=True)),
    }
    if pd.api.types.is_numeric_dtype(s):
        valid = s.dropna()
        if len(valid):
            base.update({
                "min":    round(float(valid.min()), 4),
                "max":    round(float(valid.max()), 4),
                "mean":   round(float(valid.mean()), 4),
                "median": round(float(valid.median()), 4),
                "std":    round(float(valid.std(ddof=1)), 4) if len(valid) > 1 else 0.0,
            })
    return base


@router.get("/{dataset_id}")
def get_quality_profile(dataset_id: str):
    """Return a full data quality report for the specified dataset."""
    try:
        df   = get_df(dataset_id)
        info = get_info(dataset_id)
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # ── Column profiles ──────────────────────────────────────────────────────
    columns = [_column_profile(df, c) for c in df.columns]

    # ── Date quality ─────────────────────────────────────────────────────────
    dup_dates = int(df["date"].duplicated().sum())
    date_gaps = _date_gaps(df["date"], threshold_days=3)
    total_gap_days = sum(g["missing_days"] for g in date_gaps)

    # ── PM2.5 outliers ────────────────────────────────────────────────────────
    pm25_valid = df.dropna(subset=["pm25_mean"])
    outlier_idx = _outlier_indices(pm25_valid["pm25_mean"])
    outlier_rows = pm25_valid.loc[outlier_idx, ["date", "pm25_mean"]].copy()
    outlier_rows["date"] = outlier_rows["date"].dt.strftime("%Y-%m-%d")
    outlier_list = [
        {"date": r["date"], "pm25_mean": round(r["pm25_mean"], 3)}
        for _, r in outlier_rows.head(20).iterrows()
    ]

    q1  = float(pm25_valid["pm25_mean"].quantile(0.25))
    q3  = float(pm25_valid["pm25_mean"].quantile(0.75))
    iqr = q3 - q1
    outlier_bounds = {
        "lower_fence": round(q1 - 1.5 * iqr, 3),
        "upper_fence": round(q3 + 1.5 * iqr, 3),
        "method": "Tukey IQR (Q1 − 1.5×IQR,  Q3 + 1.5×IQR)",
    }

    # ── Quality issues list ───────────────────────────────────────────────────
    issues: list[dict] = []

    null_pm25_pct = df["pm25_mean"].isna().mean() * 100
    if null_pm25_pct > 0:
        issues.append({
            "severity": "warning" if null_pm25_pct < 30 else "error",
            "field": "pm25_mean",
            "message": f"{null_pm25_pct:.1f}% of PM2.5 values are missing.",
        })

    if dup_dates > 0:
        issues.append({
            "severity": "warning",
            "field": "date",
            "message": f"{dup_dates} duplicate date(s) present.",
        })

    if len(date_gaps) > 0:
        issues.append({
            "severity": "info",
            "field": "date",
            "message": (
                f"{len(date_gaps)} date gap(s) totalling {total_gap_days} missing days "
                "(gaps > 3 consecutive days)."
            ),
        })

    neg_count = int((df["pm25_mean"].dropna() < 0).sum())
    if neg_count > 0:
        issues.append({
            "severity": "warning",
            "field": "pm25_mean",
            "message": f"{neg_count} negative PM2.5 value(s) — physically implausible.",
        })

    extreme_count = int((df["pm25_mean"].dropna() > 500).sum())
    if extreme_count > 0:
        issues.append({
            "severity": "warning",
            "field": "pm25_mean",
            "message": f"{extreme_count} PM2.5 value(s) exceed 500 µg/m³ — possible anomaly.",
        })

    if len(outlier_rows) > 0:
        issues.append({
            "severity": "info",
            "field": "pm25_mean",
            "message": (
                f"{len(outlier_rows)} statistical outlier(s) detected "
                f"(outside Tukey fences)."
            ),
        })

    # ── Quality score (0–100) ─────────────────────────────────────────────────
    score = 100
    score -= min(30, int(null_pm25_pct))          # missing values
    score -= min(10, dup_dates * 2)                # duplicate dates
    score -= min(10, len(date_gaps) * 2)           # date gaps
    score -= min(5, neg_count * 2)                 # negative values
    score -= min(5, extreme_count)                 # extreme values
    score = max(0, score)

    # ── Preprocessing recommendations ────────────────────────────────────────
    recommendations: list[str] = []
    if null_pm25_pct > 0:
        recommendations.append(
            "Forward-fill or interpolate missing PM2.5 values for time-series modelling."
        )
    if dup_dates > 0:
        recommendations.append("Remove or aggregate duplicate date entries.")
    if len(date_gaps) > 3:
        recommendations.append(
            "Large date gaps may affect lag-based feature engineering. "
            "Resample to a daily calendar index and mark gaps explicitly."
        )
    if len(outlier_rows) > 0:
        recommendations.append(
            "Consider winsorising extreme outliers (cap at Q3 + 3×IQR) "
            "before regression, but preserve raw values for reporting."
        )
    if not recommendations:
        recommendations.append("No preprocessing issues found. Dataset is clean.")

    return {
        "dataset_id": dataset_id,
        "dataset_name": info.name,
        "shape": {"rows": len(df), "columns": len(df.columns)},
        "valid_pm25_rows": info.rows,
        "columns": columns,
        "date_gaps": date_gaps[:50],          # cap at 50 for API size
        "total_gap_days": total_gap_days,
        "duplicate_dates": dup_dates,
        "outliers": {
            "count": len(outlier_rows),
            "bounds": outlier_bounds,
            "examples": outlier_list,
        },
        "quality_issues": issues,
        "quality_score": score,
        "preprocessing_recommendations": recommendations,
    }


@router.get("/{dataset_id}/cleaned")
def download_cleaned(dataset_id: str):
    """Download the cleaned version of the dataset as CSV.

    'Cleaned' means: dates parsed, rows sorted by date, duplicate dates
    removed (last kept), and non-numeric pm25_mean rows dropped.
    Raw data on disk is never modified.
    """
    try:
        df = get_df(dataset_id)
        info = get_info(dataset_id)
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    cleaned = df.dropna(subset=["pm25_mean"]).sort_values("date").drop_duplicates("date", keep="last")
    cleaned = cleaned.copy()
    cleaned["date"] = cleaned["date"].dt.strftime("%Y-%m-%d")

    csv_bytes = cleaned.to_csv(index=False).encode("utf-8")
    filename = f"{info.name.lower().replace(' ', '_').replace('(', '').replace(')', '')}_cleaned.csv"

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
