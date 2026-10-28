"""Evaluate next-calendar-day PM2.5 forecasts for AirAware."""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

DATA = Path("data/processed/city_daily.csv")
REPORT_DIR = Path("reports")
METRICS_FILE = REPORT_DIR / "forecast_metrics.csv"
PREDICTIONS_FILE = REPORT_DIR / "forecast_predictions.csv"

FEATURES = [
    "pm25_today",
    "pm25_lag1",
    "pm25_lag2",
    "pm25_lag3",
    "pm25_lag7",
    "rolling_mean_3",
    "rolling_mean_7",
]


def make_city_features(city_df):
    """Build features using observations available on or before date t."""

    city_df = city_df.copy()
    city_df["date"] = pd.to_datetime(city_df["date"], errors="coerce")
    city_df["pm25_mean"] = pd.to_numeric(
        city_df["pm25_mean"], errors="coerce"
    )

    city_df = city_df.dropna(subset=["date", "pm25_mean"])
    city_df = city_df.sort_values("date")

    # Ensure every calendar date exists. Missing observations stay NaN.
    city_df = (
        city_df.set_index("date")[["pm25_mean"]]
        .groupby(level=0)
        .mean()
        .asfreq("D")
    )

    s = city_df["pm25_mean"]
    features = pd.DataFrame(index=city_df.index)

    # Values known at the end of the forecast origin date.
    features["pm25_today"] = s
    features["pm25_lag1"] = s.shift(1)
    features["pm25_lag2"] = s.shift(2)
    features["pm25_lag3"] = s.shift(3)
    features["pm25_lag7"] = s.shift(7)

    # Rolling statistics use only observations available through date t.
    features["rolling_mean_3"] = s.rolling(
        window=3, min_periods=3
    ).mean()
    features["rolling_mean_7"] = s.rolling(
        window=7, min_periods=7
    ).mean()

    # A sample dated t predicts the observation on calendar date t + 1.
    features["target_date"] = features.index + pd.Timedelta(days=1)
    features["actual_next_day"] = s.shift(-1)

    # Keep samples only when all features and the next-day target exist.
    samples = features.dropna(
        subset=FEATURES + ["actual_next_day"]
    ).copy()

    return samples


def evaluate_city(city, city_df):
    samples = make_city_features(city_df)

    if len(samples) < 50:
        print(
            f"Skipping {city}: only {len(samples)} usable samples; "
            "at least 50 are required."
        )
        return [], []

    # Chronological split: earliest 80% for training, latest 20% for testing.
    split = int(len(samples) * 0.8)
    train = samples.iloc[:split]
    test = samples.iloc[split:]

    if len(train) < 30 or len(test) < 10:
        print(f"Skipping {city}: insufficient training or test samples.")
        return [], []

    X_train = train[FEATURES]
    y_train = train["actual_next_day"]
    X_test = test[FEATURES]
    y_test = test["actual_next_day"]

    # Baseline: predict tomorrow using today's observed PM2.5.
    baseline_pred = X_test["pm25_today"].to_numpy()

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    rf_pred = model.predict(X_test)

    results = []
    predictions = []

    for model_name, predicted in [
        ("Persistence", baseline_pred),
        ("RandomForest", rf_pred),
    ]:
        mae = mean_absolute_error(y_test, predicted)
        rmse = np.sqrt(mean_squared_error(y_test, predicted))
        r2 = (
            r2_score(y_test, predicted)
            if len(y_test) >= 2
            else np.nan
        )

        results.append({
            "city": city,
            "model": model_name,
            "train_samples": len(train),
            "test_samples": len(test),
            "train_end_date": train["target_date"].iloc[-1],
            "test_start_date": test["target_date"].iloc[0],
            "test_end_date": test["target_date"].iloc[-1],
            "MAE": mae,
            "RMSE": rmse,
            "R2": r2,
        })

        for date, actual, prediction in zip(
            test["target_date"], y_test, predicted
        ):
            predictions.append({
                "city": city,
                "model": model_name,
                "date": date,
                "actual_pm25": actual,
                "predicted_pm25": prediction,
                "absolute_error": abs(actual - prediction),
            })

    return results, predictions


def main():
    if not DATA.exists():
        raise FileNotFoundError(
            f"{DATA} not found. Run src.aggregate_city first."
        )

    df = pd.read_csv(DATA)

    required = {"city", "date", "pm25_mean"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    all_metrics = []
    all_predictions = []

    for city, city_df in df.groupby("city"):
        metrics, predictions = evaluate_city(city, city_df)
        all_metrics.extend(metrics)
        all_predictions.extend(predictions)

    if not all_metrics:
        raise RuntimeError(
            "No cities could be evaluated. Check date coverage and data."
        )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    metrics_df = pd.DataFrame(all_metrics)
    predictions_df = pd.DataFrame(all_predictions)

    metrics_df.to_csv(METRICS_FILE, index=False)
    predictions_df.to_csv(PREDICTIONS_FILE, index=False)

    print("\nAIR AWARE — NEXT-DAY FORECAST EVALUATION")
    print("=" * 65)
    print(
        metrics_df[
            [
                "city", "model", "train_samples", "test_samples",
                "MAE", "RMSE", "R2",
            ]
        ].round(3).to_string(index=False)
    )

    print(f"\nMetrics saved to: {METRICS_FILE}")
    print(f"Predictions saved to: {PREDICTIONS_FILE}")
    print(
        "\nLower MAE and RMSE indicate better predictions. "
        "Compare Random Forest against Persistence for each city."
    )


if __name__ == "__main__":
    main()