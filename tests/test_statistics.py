"""Tests for GET /statistics/overview."""

from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
ALL_CITIES = {"Mumbai", "Nagpur", "Nashik", "Pune"}


def _stats():
    r = client.get("/statistics/overview")
    assert r.status_code == 200
    return r.json()


class TestShape:
    def test_200(self):
        assert client.get("/statistics/overview").status_code == 200

    def test_top_level_keys(self):
        body = _stats()
        assert set(body.keys()) == {"kpis", "city_summary", "boxplots", "coverage"}

    def test_kpis_keys(self):
        kpis = _stats()["kpis"]
        for k in ("highest_avg_city", "highest_avg_pm25", "most_variable_city",
                  "most_variable_std", "total_valid_measurements"):
            assert k in kpis

    def test_all_cities_in_summary(self):
        body = _stats()
        cities = {r["city"] for r in body["city_summary"]}
        assert cities == ALL_CITIES

    def test_all_cities_in_boxplots(self):
        bp = _stats()["boxplots"]
        assert set(bp.keys()) == ALL_CITIES

    def test_all_cities_in_coverage(self):
        cov = {r["city"] for r in _stats()["coverage"]}
        assert cov == ALL_CITIES


class TestStatValues:
    def test_mean_le_max(self):
        for row in _stats()["city_summary"]:
            assert row["mean"] <= row["maximum"]

    def test_std_positive(self):
        for row in _stats()["city_summary"]:
            assert row["std"] > 0

    def test_valid_days_positive(self):
        for row in _stats()["city_summary"]:
            assert row["valid_days"] > 0

    def test_median_between_extremes(self):
        for row in _stats()["city_summary"]:
            assert row["mean"] > 0  # sanity; dataset is non-zero

    def test_total_valid_measurements_correct(self):
        body = _stats()
        total = sum(r["valid_days"] for r in body["city_summary"])
        assert body["kpis"]["total_valid_measurements"] == total


class TestBoxplots:
    def test_boxplot_keys(self):
        bp = _stats()["boxplots"]["Pune"]
        for k in ("q1", "median", "q3", "lower_fence", "upper_fence",
                  "min_non_outlier", "max_non_outlier", "outliers"):
            assert k in bp

    def test_q1_le_median_le_q3(self):
        bp = _stats()["boxplots"]["Pune"]
        assert bp["q1"] <= bp["median"] <= bp["q3"]

    def test_outliers_is_list(self):
        bp = _stats()["boxplots"]["Pune"]
        assert isinstance(bp["outliers"], list)

    def test_outliers_outside_fences(self):
        for city in ALL_CITIES:
            bp = _stats()["boxplots"][city]
            for v in bp["outliers"]:
                # Use >= / <= to handle values that sit exactly on the fence
                # after 4-decimal rounding (e.g. outlier=138.0, fence=138.0).
                assert v <= bp["lower_fence"] or v >= bp["upper_fence"]


class TestCoverage:
    def test_coverage_keys(self):
        row = _stats()["coverage"][0]
        for k in ("city", "first_date", "last_date", "available_rows",
                  "valid_pm25_days", "missing_pm25_rows", "avg_station_count"):
            assert k in row

    def test_missing_pm25_rows_non_negative(self):
        for row in _stats()["coverage"]:
            assert row["missing_pm25_rows"] >= 0

    def test_valid_plus_missing_equals_available(self):
        for row in _stats()["coverage"]:
            assert row["valid_pm25_days"] + row["missing_pm25_rows"] == row["available_rows"]

    def test_dates_iso_format(self):
        from datetime import datetime
        for row in _stats()["coverage"]:
            datetime.strptime(row["first_date"], "%Y-%m-%d")
            datetime.strptime(row["last_date"], "%Y-%m-%d")
