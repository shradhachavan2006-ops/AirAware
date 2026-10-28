"""Forecast endpoints — future PM2.5 predictions for each city.

GET /forecast/cities
    Returns the list of cities for which future forecasting is available,
    along with the maximum supported horizon and a model note.

GET /forecast/{city}?horizon=7
    Returns a future PM2.5 forecast for one city.
    - horizon: 7 or 14 days ahead of the latest observed date.
    - historical_tail: last 30 historical PM2.5 observations for chart context.
    - forecast: list of {target_date, predicted_pm25, horizon_day} objects.
    - latest_observed_date: the date from which the forecast starts.
    - feature_importance: per-feature RF importance scores.
    - model_note: training summary (number of samples, date range).
    - disclaimer: explicit model limitation statement.

GET /forecast/{city}/download?horizon=7
    Returns the forecast as a CSV file for download.

Design notes
-----------
* All forecasts are generated BEYOND the last available observation — never
  from the historical test period.
* Per-city models are trained on the complete available history with the same
  feature construction used in src/forecast.py (lags 1/2/3/7, rolling 3/7).
* Models are cached in-process; see backend/forecast_engine.py.
* The response includes an explicit disclaimer field to prevent misinterpretation.
"""

from __future__ import annotations

import io

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.data_loader import load_daily_data
from backend.forecast_engine import (
    MAX_HORIZON,
    get_available_cities,
    run_forecast,
)

router = APIRouter(prefix="/forecast", tags=["Forecast"])

_ALLOWED_HORIZONS = {7, 14}
_HISTORY_TAIL = 30   # days of recent history to include for chart context


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_horizon(horizon: int) -> None:
    if horizon not in _ALLOWED_HORIZONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"horizon must be one of {sorted(_ALLOWED_HORIZONS)}, got {horizon}. "
                "Use 7 for a 7-day forecast or 14 for a 14-day forecast."
            ),
        )


def _get_historical_tail(city: str, n: int = _HISTORY_TAIL) -> list[dict]:
    """Return the last ``n`` non-NaN PM2.5 observations for a city."""
    df = load_daily_data()
    city_df = df[df["city"] == city].dropna(subset=["pm25_mean"]).sort_values("date")
    tail = city_df.tail(n)
    return [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "pm25_mean": round(float(row["pm25_mean"]), 3),
            "is_forecast": False,
        }
        for _, row in tail.iterrows()
    ]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/cities")
def get_forecast_cities():
    """Return cities available for future forecasting.

    A city is available only when it has enough historical data to train the
    model reliably (at least 70 valid daily observations).
    """
    cities = get_available_cities()
    if not cities:
        raise HTTPException(
            status_code=503,
            detail=(
                "No cities have sufficient data for forecasting. "
                "Collect more observations and retry."
            ),
        )
    return {
        "cities": cities,
        "max_horizon": MAX_HORIZON,
        "supported_horizons": sorted(_ALLOWED_HORIZONS),
        "model": "RandomForest",
        "note": (
            "Each city model is trained on its full available history. "
            "These are future estimates, not historical test-period predictions."
        ),
    }


@router.get("/{city}")
def get_city_forecast(
    city: str,
    horizon: int = Query(
        7,
        description="Number of future days to forecast. Supported: 7 or 14.",
        ge=1,
        le=MAX_HORIZON,
    ),
):
    """Return a future PM2.5 forecast for one city.

    Includes:
    - ``historical_tail``: the last 30 observed (non-NaN) PM2.5 values for
      chart context. These are clearly marked with ``is_forecast: false``.
    - ``forecast``: predicted PM2.5 for each future day, marked with
      ``is_forecast: true``. Dates start from latest_observed_date + 1 day.
    - ``chart_series``: concatenation of historical_tail + forecast for
      convenience (single array for charting).
    - ``feature_importance``: RF feature importances for transparency.
    - ``model_note``: training summary.
    - ``disclaimer``: explicit limitation statement.
    """
    _validate_horizon(horizon)

    available = get_available_cities()
    if city not in available:
        raise HTTPException(
            status_code=404,
            detail=(
                f"City '{city}' is not available for forecasting. "
                f"Available: {available}."
            ),
        )

    try:
        result = run_forecast(city, horizon)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Historical tail for chart context
    historical_tail = _get_historical_tail(city)

    # Forecast points with is_forecast flag
    forecast_series = [
        {
            "date": pt.target_date,
            "pm25_mean": pt.predicted_pm25,
            "is_forecast": True,
            "horizon_day": pt.horizon_day,
        }
        for pt in result.forecast
    ]

    # Combined chart series: history + forecast (no overlap possible because
    # forecast starts from latest_observed_date + 1)
    chart_series = historical_tail + forecast_series

    return {
        "city": result.city,
        "horizon": result.horizon,
        "latest_observed_date": result.latest_observed_date,
        "latest_observed_pm25": result.latest_observed_pm25,
        "historical_tail": historical_tail,
        "forecast": [
            {
                "date": pt.target_date,
                "predicted_pm25": pt.predicted_pm25,
                "horizon_day": pt.horizon_day,
            }
            for pt in result.forecast
        ],
        "chart_series": chart_series,
        "train_rows": result.train_rows,
        "feature_importance": result.feature_importance,
        "model_note": result.model_note,
        "disclaimer": result.disclaimer,
    }


@router.get("/{city}/download")
def download_city_forecast(
    city: str,
    horizon: int = Query(
        7,
        description="Number of future days to forecast. Supported: 7 or 14.",
        ge=1,
        le=MAX_HORIZON,
    ),
):
    """Download the future PM2.5 forecast as a CSV file.

    The CSV includes columns: city, target_date, predicted_pm25, horizon_day.
    Historical observations are NOT included in the download CSV.
    """
    _validate_horizon(horizon)

    available = get_available_cities()
    if city not in available:
        raise HTTPException(
            status_code=404,
            detail=f"City '{city}' not available for forecasting. Available: {available}.",
        )

    try:
        result = run_forecast(city, horizon)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    rows = [
        {
            "city": result.city,
            "target_date": pt.target_date,
            "predicted_pm25": pt.predicted_pm25,
            "horizon_day": pt.horizon_day,
        }
        for pt in result.forecast
    ]

    df = pd.DataFrame(rows)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    filename = f"{city.lower()}_pm25_forecast_{horizon}day.csv"

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
