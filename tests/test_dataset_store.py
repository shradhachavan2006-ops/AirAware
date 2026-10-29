"""Unit tests for backend/dataset_store.py."""

from __future__ import annotations

import io
import pandas as pd
import pytest

from backend.dataset_store import (
    DEMO_IDS,
    delete_upload,
    get_df,
    get_info,
    get_pm25_series,
    list_datasets,
    register_upload,
)


def test_list_datasets_contains_all_demos():
    datasets = list_datasets()
    ids = {d.id for d in datasets}
    for demo_id in DEMO_IDS:
        assert demo_id in ids


def test_get_demo_df_and_info():
    for demo_id, city_name in DEMO_IDS.items():
        df = get_df(demo_id)
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "date" in df.columns
        assert "pm25_mean" in df.columns

        info = get_info(demo_id)
        assert info.id == demo_id
        assert info.is_demo is True
        assert info.city_hint.lower() == city_name
        assert info.rows == len(df.dropna(subset=["pm25_mean"]))


def test_get_df_unknown_raises_key_error():
    with pytest.raises(KeyError, match="not found"):
        get_df("nonexistent_dataset_id_12345")


def test_get_pm25_series():
    s = get_pm25_series("demo:pune")
    assert isinstance(s, pd.Series)
    assert not s.empty
    assert s.isna().sum() == 0


def test_register_upload_valid_lifecycle():
    # Create valid synthetic dataset (20 rows)
    dates = pd.date_range("2024-01-01", periods=20, freq="D")
    raw_df = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "pm25_mean": [25.0 + i for i in range(20)],
        "city": ["TestCity"] * 20,
    })

    info, warnings = register_upload(raw_df, "Test Dataset")
    assert info.name == "Test Dataset"
    assert info.city_hint == "Testcity"
    assert info.is_demo is False
    assert info.rows == 20
    assert not info.has_station_count
    assert not info.has_coverage_pct

    # Confirm it can be retrieved
    retrieved_df = get_df(info.id)
    assert len(retrieved_df) == 20

    retrieved_info = get_info(info.id)
    assert retrieved_info.name == "Test Dataset"

    # Confirm delete works
    assert delete_upload(info.id) is True
    # Confirm it is no longer retrievable
    with pytest.raises(KeyError):
        get_df(info.id)


def test_delete_demo_returns_false():
    # Attempting to delete a demo dataset must fail
    assert delete_upload("demo:pune") is False
    # Demo dataset must still exist
    assert get_info("demo:pune").is_demo is True


def test_register_upload_missing_columns():
    df = pd.DataFrame({"some_col": [1, 2, 3]})
    with pytest.raises(ValueError, match="Missing required column"):
        register_upload(df, "Invalid Cols")


def test_register_upload_too_few_rows():
    df = pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "pm25_mean": [12.0, 14.0, 16.0],
    })
    with pytest.raises(ValueError, match="At least 10 required"):
        register_upload(df, "Too Short")


def test_register_upload_unparseable_dates():
    df = pd.DataFrame({
        "date": ["not-a-date"] * 15,
        "pm25_mean": [20.0] * 15,
    })
    with pytest.raises(ValueError, match="unparseable dates"):
        register_upload(df, "Bad Dates")


def test_register_upload_non_numeric_pm25():
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=15).strftime("%Y-%m-%d"),
        "pm25_mean": ["invalid"] * 15,
    })
    with pytest.raises(ValueError, match="non-numeric"):
        register_upload(df, "Bad PM25")


def test_register_upload_with_warnings():
    # Generate data with negative value, duplicate date, and extreme value
    dates = ["2024-01-01"] * 2 + [f"2024-01-{i:02d}" for i in range(2, 16)]
    pm25 = [-5.0, 20.0, 600.0] + [25.0] * 13
    df = pd.DataFrame({"date": dates, "pm25_mean": pm25})

    info, warnings = register_upload(df, "Warning Dataset")
    try:
        assert any("negative" in w.lower() for w in warnings)
        assert any("500" in w for w in warnings)
        assert any("duplicate" in w.lower() for w in warnings)
    finally:
        delete_upload(info.id)
