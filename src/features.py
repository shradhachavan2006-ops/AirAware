"""Leakage-aware feature engineering for one-day-ahead city-level PM2.5 forecasts."""
import pandas as pd

FEATURE_COLUMNS = [
    "city", "pm25_lag_1", "pm25_lag_2", "pm25_lag_3", "pm25_lag_7",
    "rolling_mean_3", "rolling_mean_7", "rolling_std_7",
    "target_day_of_week", "target_month", "target_doy_sin", "target_doy_cos"
]

def make_supervised_data(df: pd.DataFrame) -> pd.DataFrame:
    required = {"city", "date", "pm25_mean"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    parts = []
    data = df.copy()
    data["date"] = pd.to_datetime(data["date"])
    data = data.sort_values(["city", "date"])

    for city, group in data.groupby("city"):
        g = group.sort_values("date").copy().set_index("date")
        # Reindex to a daily calendar so missing dates are not silently treated as adjacent days.
        full_index = pd.date_range(g.index.min(), g.index.max(), freq="D")
        g = g.reindex(full_index)
        g.index.name = "date"
        g["city"] = city

        y = pd.to_numeric(g["pm25_mean"], errors="coerce")
        g["pm25_lag_1"] = y.shift(1)
        g["pm25_lag_2"] = y.shift(2)
        g["pm25_lag_3"] = y.shift(3)
        g["pm25_lag_7"] = y.shift(7)
        past = y.shift(1)
        g["rolling_mean_3"] = past.rolling(3, min_periods=3).mean()
        g["rolling_mean_7"] = past.rolling(7, min_periods=7).mean()
        g["rolling_std_7"] = past.rolling(7, min_periods=7).std()

        target_dates = g.index + pd.Timedelta(days=1)
        g["target_day_of_week"] = target_dates.day_of_week
        g["target_month"] = target_dates.month
        doy = target_dates.day_of_year
        g["target_doy_sin"] = __import__("numpy").sin(2 * __import__("numpy").pi * doy / 365.25)
        g["target_doy_cos"] = __import__("numpy").cos(2 * __import__("numpy").pi * doy / 365.25)
        g["target"] = y.shift(-1)
        g["date"] = g.index
        g = g.reset_index(drop=True)
        parts.append(g)

    out = pd.concat(parts, ignore_index=True)
    out = out.dropna(subset=FEATURE_COLUMNS + ["target"])
    # Require truly consecutive target dates and feature dates; missing target days are excluded above.
    out["target_date"] = pd.to_datetime(out["date"]) + pd.Timedelta(days=1)
    return out[["date", "target_date"] + FEATURE_COLUMNS + ["target"]].reset_index(drop=True)

def build_next_day_features(city_df: pd.DataFrame):
    """Build one feature row from a city's latest contiguous daily observations.

    city_df must contain city, date, pm25_mean. Returns None if data is insufficient.
    """
    import numpy as np
    g = city_df.copy()
    g["date"] = pd.to_datetime(g["date"])
    g = g.sort_values("date").set_index("date")
    if g.empty:
        return None
    full_index = pd.date_range(g.index.min(), g.index.max(), freq="D")
    g = g.reindex(full_index)
    y = pd.to_numeric(g["pm25_mean"], errors="coerce")
    if len(y) < 8 or y.tail(7).isna().any() or pd.isna(y.iloc[-1]):
        return None

    target_date = g.index[-1] + pd.Timedelta(days=1)
    doy = target_date.day_of_year
    row = {
        "city": str(city_df["city"].iloc[-1]),
        "pm25_lag_1": y.iloc[-1],
        "pm25_lag_2": y.iloc[-2],
        "pm25_lag_3": y.iloc[-3],
        "pm25_lag_7": y.iloc[-7],
        "rolling_mean_3": y.iloc[-3:].mean(),
        "rolling_mean_7": y.iloc[-7:].mean(),
        "rolling_std_7": y.iloc[-7:].std(),
        "target_day_of_week": target_date.day_of_week,
        "target_month": target_date.month,
        "target_doy_sin": np.sin(2 * np.pi * doy / 365.25),
        "target_doy_cos": np.cos(2 * np.pi * doy / 365.25),
    }
    return pd.DataFrame([row], columns=FEATURE_COLUMNS)
