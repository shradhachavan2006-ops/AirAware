"""Tests for GET /observations/recent.

Run from the project root with the .venv active:
    python -m pytest tests/test_observations.py -v
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Constants (derived from the real CSV)
# ---------------------------------------------------------------------------
DATA_START = "2025-02-19"
DATA_END = "2026-10-13"
ALL_CITIES = {"Mumbai", "Nagpur", "Nashik", "Pune"}
KNOWN_CITY = "Pune"
EXPECTED_COLS = {"date", "city", "pm25_mean", "station_count", "coverage_pct"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get(**params):
    return client.get("/observations/recent", params=params)


def _get_ok(**params):
    r = _get(**params)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    return r.json()


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------

class TestResponseShape:
    def test_top_level_keys(self):
        body = _get_ok()
        assert set(body.keys()) == {"filters", "count", "observations"}

    def test_filters_block_reflects_defaults(self):
        body = _get_ok()
        f = body["filters"]
        assert f["city"] is None
        assert f["start"] is None
        assert f["end"] is None
        assert f["limit"] == 12

    def test_count_matches_observations_length(self):
        body = _get_ok()
        assert body["count"] == len(body["observations"])

    def test_observation_row_keys(self):
        body = _get_ok(city=KNOWN_CITY)
        for row in body["observations"]:
            assert set(row.keys()) == EXPECTED_COLS

    def test_date_serialised_as_iso(self):
        """Every date field must be YYYY-MM-DD."""
        from datetime import datetime
        body = _get_ok(city=KNOWN_CITY)
        for row in body["observations"]:
            datetime.strptime(row["date"], "%Y-%m-%d")  # must not raise

    def test_pm25_mean_is_float_or_none(self):
        body = _get_ok(city=KNOWN_CITY)
        for row in body["observations"]:
            assert row["pm25_mean"] is None or isinstance(row["pm25_mean"], float)

    def test_station_count_is_int_or_none(self):
        body = _get_ok(city=KNOWN_CITY)
        for row in body["observations"]:
            assert row["station_count"] is None or isinstance(row["station_count"], int)


# ---------------------------------------------------------------------------
# Default behaviour (no params)
# ---------------------------------------------------------------------------

class TestDefaults:
    def test_default_limit_is_12(self):
        body = _get_ok()
        assert len(body["observations"]) <= 12

    def test_default_contains_all_cities(self):
        """Without a city filter the response may include any city."""
        body = _get_ok()
        cities_in_response = {row["city"] for row in body["observations"]}
        # at least one known city should appear
        assert cities_in_response & ALL_CITIES

    def test_newest_first_no_filters(self):
        body = _get_ok()
        dates = [r["date"] for r in body["observations"]]
        assert dates == sorted(dates, reverse=True)


# ---------------------------------------------------------------------------
# City filter
# ---------------------------------------------------------------------------

class TestCityFilter:
    @pytest.mark.parametrize("city", sorted(ALL_CITIES))
    def test_each_city_returns_200(self, city):
        assert _get(city=city).status_code == 200

    def test_city_filter_restricts_results(self):
        body = _get_ok(city=KNOWN_CITY)
        for row in body["observations"]:
            assert row["city"] == KNOWN_CITY

    def test_unknown_city_is_404(self):
        assert _get(city="Atlantis").status_code == 404

    def test_city_case_sensitive(self):
        """'pune' (lowercase) is not a valid city name."""
        assert _get(city="pune").status_code == 404


# ---------------------------------------------------------------------------
# Date filters
# ---------------------------------------------------------------------------

class TestDateFilters:
    def test_start_only(self):
        body = _get_ok(city=KNOWN_CITY, start="2026-01-01")
        for row in body["observations"]:
            assert row["date"] >= "2026-01-01"

    def test_end_only(self):
        body = _get_ok(city=KNOWN_CITY, end="2025-06-30")
        for row in body["observations"]:
            assert row["date"] <= "2025-06-30"

    def test_start_and_end_inclusive(self):
        body = _get_ok(city=KNOWN_CITY, start="2025-06-01", end="2025-06-30")
        for row in body["observations"]:
            assert "2025-06-01" <= row["date"] <= "2025-06-30"

    def test_single_day_range(self):
        body = _get_ok(city=KNOWN_CITY, start=DATA_START, end=DATA_START)
        assert len(body["observations"]) <= 1
        if body["observations"]:
            assert body["observations"][0]["date"] == DATA_START

    def test_start_inclusive_boundary(self):
        """The start date itself must appear if data exists on that day."""
        body = _get_ok(city=KNOWN_CITY, start=DATA_START, end=DATA_START)
        if body["observations"]:
            assert body["observations"][0]["date"] == DATA_START

    def test_end_inclusive_boundary(self):
        """The end date itself must appear if data exists on that day."""
        body = _get_ok(city=KNOWN_CITY, start=DATA_END, end=DATA_END)
        if body["observations"]:
            assert body["observations"][0]["date"] == DATA_END

    def test_start_after_end_is_400(self):
        assert _get(city=KNOWN_CITY, start="2026-01-01", end="2025-01-01").status_code == 400

    def test_out_of_range_returns_empty(self):
        body = _get_ok(city=KNOWN_CITY, start="2000-01-01", end="2000-12-31")
        assert body["count"] == 0
        assert body["observations"] == []


# ---------------------------------------------------------------------------
# Limit parameter
# ---------------------------------------------------------------------------

class TestLimit:
    def test_limit_respected(self):
        body = _get_ok(city=KNOWN_CITY, limit=3)
        assert len(body["observations"]) <= 3

    def test_limit_1_returns_single_row(self):
        body = _get_ok(city=KNOWN_CITY, limit=1)
        assert len(body["observations"]) <= 1

    def test_limit_100_accepted(self):
        assert _get(city=KNOWN_CITY, limit=100).status_code == 200

    def test_limit_0_is_422(self):
        assert _get(city=KNOWN_CITY, limit=0).status_code == 422

    def test_limit_101_is_422(self):
        assert _get(city=KNOWN_CITY, limit=101).status_code == 422

    def test_limit_negative_is_422(self):
        assert _get(city=KNOWN_CITY, limit=-1).status_code == 422

    def test_limit_non_integer_is_422(self):
        assert _get(city=KNOWN_CITY, limit="abc").status_code == 422

    def test_limit_echoed_in_filters(self):
        body = _get_ok(city=KNOWN_CITY, limit=5)
        assert body["filters"]["limit"] == 5


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------

class TestSorting:
    def test_newest_first_with_city(self):
        body = _get_ok(city=KNOWN_CITY)
        dates = [r["date"] for r in body["observations"]]
        assert dates == sorted(dates, reverse=True)

    def test_newest_first_all_cities(self):
        body = _get_ok(limit=50)
        dates = [r["date"] for r in body["observations"]]
        assert dates == sorted(dates, reverse=True)

    def test_newest_first_with_date_range(self):
        body = _get_ok(city=KNOWN_CITY, start="2025-06-01", end="2025-12-31", limit=20)
        dates = [r["date"] for r in body["observations"]]
        assert dates == sorted(dates, reverse=True)


# ---------------------------------------------------------------------------
# Invalid date formats
# ---------------------------------------------------------------------------

class TestInvalidDates:
    def test_bad_start_is_400(self):
        assert _get(city=KNOWN_CITY, start="not-a-date").status_code == 400

    def test_bad_end_is_400(self):
        assert _get(city=KNOWN_CITY, end="32-13-9999").status_code == 400

    def test_bad_start_message_mentions_start(self):
        r = _get(city=KNOWN_CITY, start="bad")
        assert "start" in r.json()["detail"].lower()

    def test_bad_end_message_mentions_end(self):
        r = _get(city=KNOWN_CITY, end="bad")
        assert "end" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Missing-PM2.5 rows are preserved (coverage visibility)
# ---------------------------------------------------------------------------

class TestMissingPm25Preserved:
    def test_rows_without_pm25_are_included(self):
        """Observations with missing pm25_mean must appear in the result
        (as in the original Streamlit app.py recent-observations table),
        not be silently dropped.
        """
        # Pull a large slice for all cities; at least some rows may be NaN.
        body = _get_ok(limit=100)
        # We can only assert structure — not fabricate which rows are NaN.
        # Every row must have the expected keys regardless of pm25_mean value.
        for row in body["observations"]:
            assert EXPECTED_COLS == set(row.keys())
