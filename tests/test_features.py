import pandas as pd
from src.features import make_supervised_data, build_next_day_features

def test_features_exclude_current_target():
    dates = pd.date_range("2024-01-01", periods=20, freq="D")
    df = pd.DataFrame({"city": "Pune", "date": dates, "pm25_mean": range(20)})
    out = make_supervised_data(df)
    assert not out.empty
    first = out.iloc[0]
    assert first["pm25_lag_1"] == 6
    assert first["target"] == 8

def test_next_day_features_requires_contiguous_history():
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    df = pd.DataFrame({"city": "Pune", "date": dates, "pm25_mean": range(10)})
    features = build_next_day_features(df)
    assert features is not None
    assert features.iloc[0]["pm25_lag_1"] == 9
