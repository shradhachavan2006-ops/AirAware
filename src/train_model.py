"""Train baseline and Random Forest models with a chronological holdout."""
from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from src.features import make_supervised_data, FEATURE_COLUMNS

DATA = Path("data/processed/city_daily.csv")
MODEL_PATH = Path("models/global_pm25_model.joblib")
META_PATH = Path("models/model_metadata.json")

def main():
    if not DATA.exists():
        raise FileNotFoundError("Run `python -m src.aggregate_city` after adding raw data.")
    daily = pd.read_csv(DATA, parse_dates=["date"])
    supervised = make_supervised_data(daily)
    if len(supervised) < 100:
        raise ValueError(f"Only {len(supervised)} supervised rows. Collect more valid history before modeling.")

    supervised = supervised.sort_values(["target_date", "city"]).reset_index(drop=True)
    unique_dates = sorted(supervised["target_date"].unique())
    test_start = unique_dates[int(len(unique_dates) * 0.85)]
    val_start = unique_dates[int(len(unique_dates) * 0.70)]

    train = supervised[supervised["target_date"] < val_start]
    valid = supervised[(supervised["target_date"] >= val_start) & (supervised["target_date"] < test_start)]
    test = supervised[supervised["target_date"] >= test_start]

    if min(len(train), len(valid), len(test)) == 0:
        raise ValueError("Chronological split produced an empty partition. Check date coverage.")

    numeric_features = [c for c in FEATURE_COLUMNS if c != "city"]
    preprocessor = ColumnTransformer(
        [("city", OneHotEncoder(handle_unknown="ignore"), ["city"]),
         ("numeric", "passthrough", numeric_features)]
    )
    candidate = Pipeline([
        ("preprocess", preprocessor),
        ("model", RandomForestRegressor(
            n_estimators=300, max_depth=10, min_samples_leaf=2,
            random_state=42, n_jobs=-1
        ))
    ])

    # Select model using validation MAE. The persistence baseline uses latest observed value (lag 1).
    candidate.fit(train[FEATURE_COLUMNS], train["target"])
    valid_pred = candidate.predict(valid[FEATURE_COLUMNS])
    valid_mae = mean_absolute_error(valid["target"], valid_pred)
    baseline_valid_mae = mean_absolute_error(valid["target"], valid["pm25_lag_1"])

    # Refit chosen model on train + validation, then evaluate once on held-out test.
    train_valid = pd.concat([train, valid]).sort_values(["target_date", "city"])
    candidate.fit(train_valid[FEATURE_COLUMNS], train_valid["target"])
    test_pred = candidate.predict(test[FEATURE_COLUMNS])
    baseline_test_pred = test["pm25_lag_1"].to_numpy()

    metrics = {
        "test_mae": float(mean_absolute_error(test["target"], test_pred)),
        "test_rmse": float(np.sqrt(mean_squared_error(test["target"], test_pred))),
        "baseline_test_mae": float(mean_absolute_error(test["target"], baseline_test_pred)),
        "baseline_test_rmse": float(np.sqrt(mean_squared_error(test["target"], baseline_test_pred))),
        "validation_mae": float(valid_mae),
        "validation_baseline_mae": float(baseline_valid_mae),
        "train_rows": int(len(train)),
        "validation_rows": int(len(valid)),
        "test_rows": int(len(test)),
        "test_start": str(pd.Timestamp(test_start).date()),
        "test_end": str(pd.Timestamp(max(test["target_date"])).date()),
        "features": FEATURE_COLUMNS,
        "target": "next-day city-level pm25_mean (ug/m3)",
        "model": "RandomForestRegressor",
        "warning": "Metrics are valid only for the dataset and split used here; inspect per-city performance and coverage."
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(candidate, MODEL_PATH)
    META_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))

if __name__ == "__main__":
    main()
