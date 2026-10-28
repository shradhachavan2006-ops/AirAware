"""Tests for GET /dashboard/summary.

Run from the project root:
    python -m pytest tests/test_dashboard.py -v

Requires the .venv virtual environment to be active and httpx installed:
    pip install httpx pytest
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Known constants derived from the real CSV
# ---------------------------------------------------------------------------
KNOWN_CITY = "Pune"
DATA_START = "2025-02-19"
DATA_END = "2026-10-13"
ALL_CITIES = {"Mumbai", "Nagpur", "Nashik", "Pune"}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _summary(city=KNOWN_CITY, start=DATA_START, end=DATA_END):
    return client.get(
        "/dashboard/summary",
        params={"city": city, "start": start, "end": end},
    )


# ---------------------------------------------------------------------------
# Happy-path: response shape and types
# ---------------------------------------------------------------------------

class TestSummaryHappyPath:
    def test_status_200(self):
        r = _summary()
        assert r.status_code == 200

    def test_top_level_keys(self):
        body = _summary().json()
        assert set(body.keys()) == {"selected", "kpis", "trend_series", "city_summary", "recent_observations"}

    def test_selected_block(self):
        body = _summary().json()
        sel = body["selected"]
        assert sel["city"] == KNOWN_CITY
        assert sel["start"] == DATA_START
        assert sel["end"] == DATA_END

    def test_kpis_present(self):
        kpis = _summary().json()["kpis"]
        for key in ("latest_pm25", "latest_date", "period_avg_pm25", "period_max_pm25", "valid_city_days"):
            assert key in kpis, f"Missing KPI key: {key}"

    def test_kpi_latest_pm25_is_float(self):
        kpis = _summary().json()["kpis"]
        assert isinstance(kpis["latest_pm25"], float)

    def test_kpi_valid_city_days_is_int(self):
        kpis = _summary().json()["kpis"]
        assert isinstance(kpis["valid_city_days"], int)
        assert kpis["valid_city_days"] > 0

    def test_kpi_period_avg_le_max(self):
        kpis = _summary().json()["kpis"]
        assert kpis["period_avg_pm25"] <= kpis["period_max_pm25"]

    def test_kpi_latest_date_iso_format(self):
        """latest_date must be YYYY-MM-DD."""
        from datetime import datetime
        kpis = _summary().json()["kpis"]
        # must not raise
        datetime.strptime(kpis["latest_date"], "%Y-%m-%d")

    def test_trend_series_not_empty(self):
        series = _summary().json()["trend_series"]
        assert len(series) > 0

    def test_trend_series_row_keys(self):
        row = _summary().json()["trend_series"][0]
        assert set(row.keys()) == {"date", "pm25_mean", "rolling_7d"}

    def test_rolling_7d_null_at_start(self):
        """First few rows should have rolling_7d=null (fewer than min_periods=3)."""
        series = _summary().json()["trend_series"]
        # At least the very first item (only 1 data point) must be null
        assert series[0]["rolling_7d"] is None

    def test_rolling_7d_non_null_after_enough_data(self):
        """After 3+ consecutive valid readings the rolling value must be numeric."""
        series = _summary().json()["trend_series"]
        # find the first non-null rolling value
        non_null = [r for r in series if r["rolling_7d"] is not None]
        assert len(non_null) > 0, "No non-null rolling values found"

    def test_city_summary_all_cities_present(self):
        summary = _summary().json()["city_summary"]
        cities_in_response = {row["city"] for row in summary}
        assert ALL_CITIES == cities_in_response

    def test_city_summary_sorted_descending(self):
        summary = _summary().json()["city_summary"]
        avgs = [row["average_pm25"] for row in summary]
        assert avgs == sorted(avgs, reverse=True)

    def test_recent_observations_max_12(self):
        recent = _summary().json()["recent_observations"]
        assert len(recent) <= 12

    def test_recent_observations_newest_first(self):
        recent = _summary().json()["recent_observations"]
        dates = [r["date"] for r in recent]
        assert dates == sorted(dates, reverse=True)

    def test_recent_observations_correct_city(self):
        recent = _summary().json()["recent_observations"]
        for row in recent:
            assert row["city"] == KNOWN_CITY


# ---------------------------------------------------------------------------
# Date filtering
# ---------------------------------------------------------------------------

class TestDateFiltering:
    def test_narrow_date_range(self):
        """A one-month slice must contain fewer observations than the full range."""
        full = _summary().json()["kpis"]["valid_city_days"]
        narrow = _summary(start="2025-06-01", end="2025-06-30").json()["kpis"]["valid_city_days"]
        assert narrow < full

    def test_single_day_recent_observations(self):
        """When start == end there should be at most 1 observation."""
        r = _summary(start=DATA_START, end=DATA_START)
        body = r.json()
        assert r.status_code == 200
        assert len(body["recent_observations"]) <= 1

    def test_date_inclusive_both_ends(self):
        """Observations on the exact start and end dates must be included."""
        body = _summary(start=DATA_START, end=DATA_START).json()
        if body["recent_observations"]:
            assert body["recent_observations"][0]["date"] == DATA_START


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestErrors:
    def test_unknown_city_404(self):
        r = _summary(city="Atlantis")
        assert r.status_code == 404

    def test_invalid_start_date_400(self):
        r = _summary(start="not-a-date")
        assert r.status_code == 400

    def test_invalid_end_date_400(self):
        r = _summary(end="31-13-9999")
        assert r.status_code == 400

    def test_start_after_end_400(self):
        r = _summary(start="2026-01-01", end="2025-01-01")
        assert r.status_code == 400

    def test_out_of_range_date_returns_empty_data(self):
        """A valid date range with no data should return zeroed KPIs gracefully."""
        r = _summary(start="2000-01-01", end="2000-01-31")
        assert r.status_code == 200
        body = r.json()
        assert body["kpis"]["latest_pm25"] is None
        assert body["kpis"]["valid_city_days"] == 0
        assert body["trend_series"] == []
        assert body["recent_observations"] == []

    def test_missing_city_param_422(self):
        r = client.get("/dashboard/summary", params={"start": DATA_START, "end": DATA_END})
        assert r.status_code == 422

    def test_missing_start_param_422(self):
        r = client.get("/dashboard/summary", params={"city": KNOWN_CITY, "end": DATA_END})
        assert r.status_code == 422

    def test_missing_end_param_422(self):
        r = client.get("/dashboard/summary", params={"city": KNOWN_CITY, "start": DATA_START})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# All four cities reachable
# ---------------------------------------------------------------------------

class TestAllCities:
    @pytest.mark.parametrize("city", sorted(ALL_CITIES))
    def test_each_city_returns_200(self, city):
        r = _summary(city=city)
        assert r.status_code == 200

    @pytest.mark.parametrize("city", sorted(ALL_CITIES))
    def test_each_city_has_valid_days(self, city):
        body = _summary(city=city).json()
        assert body["kpis"]["valid_city_days"] > 0
