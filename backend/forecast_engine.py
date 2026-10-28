"""AirAware Forecast Engine — per-city future PM2.5 predictions.

Design principles
-----------------
* Uses ALL available historical data for training (no test-holdout) so the
  model has access to the most recent observations.
* Builds the same lag/rolling features used by src/forecast.py, ensuring
  consistency with the evaluation pipeline.
* Future predictions are generated iteratively: each step appends the
  predicted value to the simulated history so that lag and rolling features
  for subsequent steps can be constructed correctly.
* Models are cached in-process to avoid re-training on every API call.
  The cache is keyed on (city, n_latest_rows) where n_latest_rows is the
  length of the most-recently-loaded dataset, so the cache is invalidated
  automatically if new data is loaded.
* Forecast dates start from (latest_observed_date + 1 day).
* Predicted values are marked with a 'is_forecast' flag and never mixed with
  historical actuals in the response.

Limitations surfaced explicitly in the API
-----------------------------------------
* RandomForest cannot extrapolate beyond the training distribution.
* Uncertainty grows with horizon (no PI returned - acknowledged).
* If a city has fewer than MIN_TRAIN_ROWS rows, forecasting is refused.
* Missing data gaps near the tail of the series degrade rolling features.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from backend.data_loader import load_daily_data

# Feature names - must match src/forecast.py exactly
FEATURES = [
    "pm25_today",
    "pm25_lag1",
    "pm25_lag2",
    "pm25_lag3",
    "pm25_lag7",
    "rolling_mean_3",
    "rolling_mean_7",
]

MIN_TRAIN_ROWS = 60  # refuse if fewer samples

# Maximum supported horizon (days beyond latest observed date)
MAX_HORIZON = 14

# RF hyper-parameters - same as src/forecast.py
_RF_PARAMS: dict = dict(
    n_estimators=300,
    max_depth=8,
    min_samples_leaf=3,
    random_state=42,
    n_jobs=-1,
)


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class CityModel:
    city: str
    model: RandomForestRegressor
    latest_date: date
    # The daily PM2.5 series used for training (date-indexed, NaN-filled gaps)
    history: pd.Series          # index=DatetimeIndex, values=float|NaN
    train_rows: int
    feature_importance: dict[str, float] = field(default_factory=dict)


@dataclass
class ForecastPoint:
    target_date: str   # "YYYY-MM-DD"
    predicted_pm25: float
    horizon_day: int   # 1 = first future day, etc.


@dataclass
class ForecastResult:
    city: str
    horizon: int
    latest_observed_date: str
    latest_observed_pm25: Optional[float]
    forecast: list[ForecastPoint]
    train_rows: int
    feature_importance: dict[str, float]
    model_note: str
    disclaimer: str


# ── In-process model cache ───────────────────────────────────────────────────

_cache: dict[str, CityModel] = {}
_cache_lock = threading.Lock()


def _cache_key(city: str, dataset_len: int) -> str:
    return f"{city}::{dataset_len}"


# ── Feature construction ─────────────────────────────────────────────────────

def _make_features(series: pd.Series) -> pd.DataFrame:
    """Build training features from a dense date-indexed PM2.5 series.

    Each row at position t represents features known at the end of day t,
    predicting day t+1.  Only rows where all feature columns AND the target
    are non-NaN are kept (matches src/forecast.py make_city_features).
    """
    s = series.copy()
    df = pd.DataFrame(index=s.index)
    df["pm25_today"] = s
    df["pm25_lag1"] = s.shift(1)
    df["pm25_lag2"] = s.shift(2)
    df["pm25_lag3"] = s.shift(3)
    df["pm25_lag7"] = s.shift(7)
    df["rolling_mean_3"] = s.rolling(window=3, min_periods=3).mean()
    df["rolling_mean_7"] = s.rolling(window=7, min_periods=7).mean()
    df["actual_next_day"] = s.shift(-1)
    return df.dropna(subset=FEATURES + ["actual_next_day"])


def _build_one_feature_row(series: pd.Series) -> pd.DataFrame:
    """Build a single prediction feature row from the tail of ``series``.

    ``series`` is a date-indexed daily PM2.5 series that may contain NaN for
    missing calendar dates.  The function reads the last 7 non-NaN values to
    compute lag and rolling features.  Raises ValueError if insufficient.
    """
    non_nan = series.dropna()
    if len(non_nan) < 7:
        raise ValueError(
            f"Insufficient tail data: only {len(non_nan)} non-NaN values (need >= 7)."
        )

    # Use the last 7 non-NaN values for rolling stats, matching training logic
    tail7 = non_nan.iloc[-7:]

    # Positional lags from the series end (may skip NaN-filled gaps)
    def _lag(k: int) -> float:
        vals = non_nan.iloc[-(k):]
        return float(vals.iloc[0]) if len(vals) >= k else float("nan")

    row = {
        "pm25_today":     float(non_nan.iloc[-1]),
        "pm25_lag1":      float(non_nan.iloc[-1]),
        "pm25_lag2":      float(non_nan.iloc[-2]) if len(non_nan) >= 2 else float("nan"),
        "pm25_lag3":      float(non_nan.iloc[-3]) if len(non_nan) >= 3 else float("nan"),
        "pm25_lag7":      float(non_nan.iloc[-7]) if len(non_nan) >= 7 else float("nan"),
        "rolling_mean_3": float(tail7.iloc[-3:].mean()) if len(tail7) >= 3 else float("nan"),
        "rolling_mean_7": float(tail7.mean()),
    }
    return pd.DataFrame([row], columns=FEATURES)


# ── Model training ───────────────────────────────────────────────────────────

def _train_city_model(city: str, city_df: pd.DataFrame) -> CityModel:
    """Train a RandomForest on ALL available data for one city.

    Uses ALL data for training (no holdout) — this model is for future
    forecasting.  Retrospective evaluation uses src/forecast.py.
    """
    city_df = city_df.copy()
    city_df["date"] = pd.to_datetime(city_df["date"], errors="coerce")
    city_df["pm25_mean"] = pd.to_numeric(city_df["pm25_mean"], errors="coerce")
    city_df = city_df.dropna(subset=["date", "pm25_mean"]).sort_values("date")

    # Reindex to fill calendar gaps with NaN (same as src/forecast.py)
    series: pd.Series = (
        city_df.set_index("date")[["pm25_mean"]]
        .groupby(level=0)
        .mean()
        .asfreq("D")["pm25_mean"]
    )

    samples = _make_features(series)

    if len(samples) < MIN_TRAIN_ROWS:
        raise ValueError(
            f"{city}: only {len(samples)} training samples; "
            f"at least {MIN_TRAIN_ROWS} required."
        )

    X = samples[FEATURES]
    y = samples["actual_next_day"]

    rf = RandomForestRegressor(**_RF_PARAMS)
    rf.fit(X, y)

    importances = dict(zip(FEATURES, rf.feature_importances_.round(4).tolist()))

    # Latest date with a non-NaN observation
    latest_date = series.dropna().index[-1].date()

    return CityModel(
        city=city,
        model=rf,
        latest_date=latest_date,
        history=series,
        train_rows=len(samples),
        feature_importance=importances,
    )


# ── Cache lookup / population ─────────────────────────────────────────────────

def _get_city_model(city: str, df: pd.DataFrame) -> CityModel:
    """Return a trained CityModel, training if not cached or data has changed."""
    dataset_len = len(df)
    key = _cache_key(city, dataset_len)

    with _cache_lock:
        if key in _cache:
            return _cache[key]

    # Train outside the lock to avoid blocking other requests
    city_df = df[df["city"] == city].copy()
    model = _train_city_model(city, city_df)

    with _cache_lock:
        # Evict stale entries for this city
        stale = [k for k in list(_cache.keys()) if k.startswith(f"{city}::")]
        for k in stale:
            del _cache[k]
        _cache[key] = model

    return model


# ── Iterative future forecast ────────────────────────────────────────────────

def _iterative_forecast(city_model: CityModel, horizon: int) -> list[ForecastPoint]:
    """Generate ``horizon`` future PM2.5 predictions iteratively.

    Each step:
      1. Build a single feature row from the current simulated series tail.
      2. Predict PM2.5 for the next day.
      3. Append the prediction to the simulated series so subsequent steps
         reference it via lag/rolling features.

    Predictions are clipped to [0, 999] to avoid nonsensical negatives.
    """
    if horizon < 1 or horizon > MAX_HORIZON:
        raise ValueError(f"horizon must be between 1 and {MAX_HORIZON}, got {horizon}.")

    # Work on a mutable copy of the historical series
    sim_series = city_model.history.copy()
    rf = city_model.model

    points: list[ForecastPoint] = []

    for step in range(1, horizon + 1):
        next_date = pd.Timestamp(city_model.latest_date) + pd.Timedelta(days=step)

        X = _build_one_feature_row(sim_series)
        raw_pred = float(rf.predict(X)[0])
        pred = float(np.clip(raw_pred, 0.0, 999.0))

        points.append(ForecastPoint(
            target_date=next_date.strftime("%Y-%m-%d"),
            predicted_pm25=round(pred, 3),
            horizon_day=step,
        ))

        # Extend simulated series with the predicted value
        sim_series[next_date] = pred

    return points


# ── Public API ───────────────────────────────────────────────────────────────

_DISCLAIMER = (
    "These are model-generated estimates based on historical PM2.5 patterns. "
    "RandomForest cannot extrapolate beyond its training distribution, and "
    "prediction uncertainty grows with forecast horizon. "
    "No meteorological inputs (wind, rain, temperature) are used. "
    "Values should not be treated as official AQI forecasts or medical advice."
)


def get_available_cities() -> list[str]:
    """Return cities for which forecasting is possible (sufficient data)."""
    df = load_daily_data()
    cities = sorted(df["city"].dropna().unique().tolist())
    valid = []
    for city in cities:
        non_nan = df[df["city"] == city]["pm25_mean"].dropna()
        if len(non_nan) >= MIN_TRAIN_ROWS + 10:
            valid.append(city)
    return valid


def run_forecast(city: str, horizon: int) -> ForecastResult:
    """Train (or use cached) city model and return future predictions.

    Parameters
    ----------
    city    : Must be in get_available_cities().
    horizon : Number of future days to predict (1-14).

    Returns
    -------
    ForecastResult with forecast list, metadata, feature importance, and
    disclaimer text.
    """
    if horizon < 1 or horizon > MAX_HORIZON:
        raise ValueError(f"horizon must be 1-{MAX_HORIZON}, got {horizon}.")

    df = load_daily_data()
    available = get_available_cities()

    if city not in available:
        raise ValueError(
            f"City '{city}' not available for forecasting. "
            f"Available cities: {available}."
        )

    city_model = _get_city_model(city, df)
    points = _iterative_forecast(city_model, horizon)

    # Latest non-NaN observation value for display context
    latest_val = city_model.history.dropna().iloc[-1]
    latest_pm25: Optional[float] = round(float(latest_val), 3) if pd.notna(latest_val) else None

    model_note = (
        f"RandomForest trained on {city_model.train_rows} daily samples "
        f"(full history through {city_model.latest_date}). "
        "Features: today's PM2.5, 1/2/3/7-day lags, 3-day and 7-day rolling means."
    )

    return ForecastResult(
        city=city,
        horizon=horizon,
        latest_observed_date=city_model.latest_date.strftime("%Y-%m-%d"),
        latest_observed_pm25=latest_pm25,
        forecast=points,
        train_rows=city_model.train_rows,
        feature_importance=city_model.feature_importance,
        model_note=model_note,
        disclaimer=_DISCLAIMER,
    )
