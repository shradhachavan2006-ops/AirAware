from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_PATH = PROJECT_ROOT / "data" / "processed" / "city_daily.csv"
METRICS_PATH = PROJECT_ROOT / "reports" / "forecast_metrics.csv"
PREDICTIONS_PATH = PROJECT_ROOT / "reports" / "forecast_predictions.csv"

DATA_COLUMNS = {
    "city",
    "date",
    "pm25_mean",
    "station_count",
    "coverage_pct",
}

METRICS_COLUMNS = {
    "city",
    "model",
    "MAE",
    "RMSE",
    "R2",
}

PREDICTIONS_COLUMNS = {
    "city",
    "model",
    "date",
    "actual_pm25",
    "predicted_pm25",
}


def _load_csv(path: Path, required_columns: set[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required data file not found: {path}")

    df = pd.read_csv(path)

    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"{path.name} is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    return df


def load_daily_data() -> pd.DataFrame:
    df = _load_csv(DATA_PATH, DATA_COLUMNS)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["city"] = df["city"].astype("string").str.strip()

    return df.dropna(subset=["city", "date"]).sort_values(
        ["city", "date"]
    ).reset_index(drop=True)


def load_forecast_metrics() -> pd.DataFrame:
    return _load_csv(METRICS_PATH, METRICS_COLUMNS)


def load_forecast_predictions() -> pd.DataFrame:
    df = _load_csv(PREDICTIONS_PATH, PREDICTIONS_COLUMNS)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    return df


if __name__ == "__main__":
    daily = load_daily_data()
    metrics = load_forecast_metrics()
    predictions = load_forecast_predictions()

    print("AirAware data-loading check")
    print("-" * 35)
    print(f"Daily records: {len(daily)}")
    print(f"Cities: {sorted(daily['city'].dropna().unique().tolist())}")
    print(
        f"Date range: {daily['date'].min().date()} "
        f"to {daily['date'].max().date()}"
    )
    print(f"Forecast metric records: {len(metrics)}")
    print(f"Forecast prediction records: {len(predictions)}")
