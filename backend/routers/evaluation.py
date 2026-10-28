"""Evaluation endpoints.

GET /evaluation/cities
    Returns the list of cities that have both metrics and prediction records,
    plus the sorted model names. Mirrors pages/4_Prediction.py's city selection.

GET /evaluation/{city}
    Returns the full evaluation data for one city:
    - Model metrics (MAE, RMSE, R²) — all columns from forecast_metrics.csv.
    - Sorted as: Persistence first, then RandomForest, then others.
    - Warning flag when RandomForest MAE > Persistence MAE (original app logic).
    - Actual-vs-predicted chart data: deduplicated actual values + per-model
      predicted series, sorted by date.
    - Per-model prediction records for the table and CSV download.

Original Streamlit semantics preserved
----------------------------------------
* Cities = sorted intersection of cities with metrics AND predictions.
* Preferred sort: {"Persistence": 0, "RandomForest": 1}, others get 99.
* Chart actual line: `actual = chart_data.sort_values("date")
      .drop_duplicates(subset=["date"])` — one actual point per date.
* `chart_data = city_predictions.dropna(subset=["date","actual_pm25",
  "predicted_pm25"])`.
* R² may be negative — returned as-is, never hidden.
* Evaluation results represent historical holdout performance only.
  The response includes an explicit ``disclaimer`` field.
* `absolute_error` column is included if present in the predictions CSV.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException

from backend.data_loader import load_forecast_metrics, load_forecast_predictions

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])

_PREFERRED_ORDER = {"Persistence": 0, "RandomForest": 1}
_DISCLAIMER = (
    "These results come from a historical holdout period and do not represent "
    "tomorrow's live forecast or an official AQI forecast."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        f = float(value)
        return None if np.isnan(f) else round(f, 6)
    except (TypeError, ValueError):
        return None


def _sort_key(model_name: str) -> int:
    return _PREFERRED_ORDER.get(model_name, 99)


def _get_valid_cities(metrics: pd.DataFrame, predictions: pd.DataFrame) -> list[str]:
    """Return cities present in both dataframes, sorted."""
    m_cities = set(metrics["city"].dropna().astype(str))
    p_cities = set(predictions["city"].dropna().astype(str))
    return sorted(m_cities & p_cities)


def _serialize_metric_row(row: pd.Series) -> dict:
    """Serialize one metrics row; includes all CSV columns."""
    result: dict[str, Any] = {}
    for col in row.index:
        if col == "_sort":
            continue
        val = row[col]
        if isinstance(val, float):
            result[col] = _safe_float(val)
        elif pd.isna(val):
            result[col] = None
        elif hasattr(val, "strftime"):
            result[col] = val.strftime("%Y-%m-%d")
        else:
            result[col] = val
    return result


def _serialize_prediction_row(row: pd.Series) -> dict:
    return {
        "date": row["date"].strftime("%Y-%m-%d") if pd.notna(row.get("date")) else None,
        "city": str(row.get("city", "")),
        "model": str(row.get("model", "")),
        "actual_pm25": _safe_float(row.get("actual_pm25")),
        "predicted_pm25": _safe_float(row.get("predicted_pm25")),
        "absolute_error": _safe_float(row.get("absolute_error")),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/cities")
def get_evaluation_cities():
    """Return cities available for evaluation and the models present."""
    metrics = load_forecast_metrics()
    predictions = load_forecast_predictions()

    required_m = {"city", "model", "MAE", "RMSE", "R2"}
    required_p = {"city", "model", "date", "actual_pm25", "predicted_pm25"}

    if not required_m.issubset(metrics.columns) or not required_p.issubset(predictions.columns):
        raise HTTPException(
            status_code=503,
            detail="Forecast report columns do not match the expected schema.",
        )

    cities = _get_valid_cities(metrics, predictions)
    if not cities:
        raise HTTPException(
            status_code=503,
            detail="No cities have both metrics and prediction records.",
        )

    models = sorted(metrics["model"].dropna().unique().tolist(), key=_sort_key)
    return {"cities": cities, "models": models}


@router.get("/{city}")
def get_city_evaluation(city: str):
    """Return full evaluation data for one city.

    Includes:
    - ``metrics``: list of model scorecards sorted Persistence → RandomForest.
    - ``rf_worse_than_persistence``: bool — mirrors the original warning logic.
    - ``chart_data``: actual values (deduplicated) + per-model predicted series.
    - ``prediction_records``: per-model record tables for table/download use.
    - ``disclaimer``: standard holdout disclaimer text.
    """
    metrics = load_forecast_metrics()
    predictions = load_forecast_predictions()

    cities = _get_valid_cities(metrics, predictions)
    if city not in cities:
        raise HTTPException(
            status_code=404,
            detail=f"City '{city}' not found. Available: {cities}.",
        )

    city_metrics = metrics[metrics["city"] == city].copy()
    city_preds = predictions[predictions["city"] == city].copy()

    # Sort metrics: Persistence → RandomForest → others
    city_metrics["_sort"] = city_metrics["model"].map(_PREFERRED_ORDER).fillna(99)
    city_metrics = city_metrics.sort_values("_sort")

    # Serialize metrics rows
    metrics_out = [_serialize_metric_row(row) for _, row in city_metrics.iterrows()]

    # RF worse than Persistence warning
    # pivot = city_metrics.set_index("model")
    pivot = city_metrics.set_index("model")
    rf_worse = False
    if (
        "Persistence" in pivot.index
        and "RandomForest" in pivot.index
        and pd.notna(pivot.loc["Persistence", "MAE"])
        and pd.notna(pivot.loc["RandomForest", "MAE"])
        and pivot.loc["RandomForest", "MAE"] > pivot.loc["Persistence", "MAE"]
    ):
        rf_worse = True

    # Chart data
    # chart_data = city_predictions.dropna(subset=["date","actual_pm25","predicted_pm25"])
    chart_data = city_preds.dropna(
        subset=["date", "actual_pm25", "predicted_pm25"]
    ).copy()

    # actual = chart_data.sort_values("date").drop_duplicates(subset=["date"])
    actual_df = (
        chart_data.sort_values("date")
        .drop_duplicates(subset=["date"])
    )
    actual_series = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "actual_pm25": _safe_float(row["actual_pm25"]),
        }
        for _, row in actual_df.iterrows()
    ]

    # Per-model predicted series
    model_series: list[dict] = []
    for model_name in sorted(chart_data["model"].dropna().unique(), key=_sort_key):
        md = chart_data[chart_data["model"] == model_name].sort_values("date")
        model_series.append(
            {
                "model": model_name,
                "data": [
                    {
                        "date": row["date"].strftime("%Y-%m-%d"),
                        "predicted_pm25": _safe_float(row["predicted_pm25"]),
                    }
                    for _, row in md.iterrows()
                ],
            }
        )

    # Per-model full prediction records (for table + download)
    prediction_records: dict[str, list[dict]] = {}
    for model_name in sorted(city_preds["model"].dropna().unique(), key=_sort_key):
        model_df = city_preds[city_preds["model"] == model_name].sort_values(
            "date", ascending=False
        )
        prediction_records[model_name] = [
            _serialize_prediction_row(row) for _, row in model_df.iterrows()
        ]

    # Test window metadata (optional columns)
    test_window: Optional[dict] = None
    if {"test_start_date", "test_end_date", "test_samples"}.issubset(
        city_metrics.columns
    ):
        starts = pd.to_datetime(
            city_metrics["test_start_date"], errors="coerce"
        ).dropna()
        ends = pd.to_datetime(
            city_metrics["test_end_date"], errors="coerce"
        ).dropna()
        samples = pd.to_numeric(
            city_metrics["test_samples"], errors="coerce"
        ).max()
        if not starts.empty and not ends.empty:
            test_window = {
                "start": starts.min().strftime("%Y-%m-%d"),
                "end": ends.max().strftime("%Y-%m-%d"),
                "max_samples": int(samples) if pd.notna(samples) else None,
            }

    return {
        "city": city,
        "test_window": test_window,
        "metrics": metrics_out,
        "rf_worse_than_persistence": rf_worse,
        "chart_data": {
            "actual": actual_series,
            "models": model_series,
        },
        "prediction_records": prediction_records,
        "disclaimer": _DISCLAIMER,
    }
