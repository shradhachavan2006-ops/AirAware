"""Tests for GET /trends/series and GET /trends/download."""

from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

CITIES = ["Mumbai", "Nagpur", "Nashik", "Pune"]
START = "2025-02-19"
END = "2026-10-13"


def _series(**params):
    return client.get("/trends/series", params=params)

def _download(**params):
    return client.get("/trends/download", params=params)


class TestSeriesShape:
    def test_single_city_200(self):
        r = _series(cities="Pune", start=START, end=END, metric="pm25_mean")
        assert r.status_code == 200

    def test_top_level_keys(self):
        body = _series(cities="Pune", start=START, end=END, metric="pm25_mean").json()
        assert set(body.keys()) == {"filters", "series", "summary"}

    def test_filters_echoed(self):
        f = _series(cities="Pune", start=START, end=END, metric="pm25_mean").json()["filters"]
        assert f["cities"] == ["Pune"]
        assert f["metric"] == "pm25_mean"
        assert f["start"] == START
        assert f["end"] == END

    def test_series_has_one_entry_per_city(self):
        body = _series(cities=["Pune", "Mumbai"], start=START, end=END, metric="pm25_mean").json()
        cities_in = {s["city"] for s in body["series"]}
        assert cities_in == {"Pune", "Mumbai"}

    def test_series_data_row_keys(self):
        body = _series(cities="Pune", start=START, end=END, metric="pm25_mean").json()
        row = body["series"][0]["data"][0]
        assert "date" in row and "pm25_mean" in row

    def test_summary_all_cities_present(self):
        body = _series(cities=CITIES, start=START, end=END, metric="pm25_mean").json()
        assert {s["city"] for s in body["summary"]} == set(CITIES)

    def test_summary_keys(self):
        body = _series(cities="Pune", start=START, end=END, metric="pm25_mean").json()
        row = body["summary"][0]
        assert set(row.keys()) == {"city", "observed_days", "average", "maximum"}

    def test_station_count_metric(self):
        r = _series(cities="Pune", start=START, end=END, metric="station_count")
        assert r.status_code == 200
        body = r.json()
        row = body["series"][0]["data"][0]
        assert "station_count" in row

    def test_null_emitted_for_missing(self):
        body = _series(cities="Pune", start=START, end=END, metric="pm25_mean").json()
        all_vals = [d["pm25_mean"] for d in body["series"][0]["data"]]
        # structure is correct even if all non-null in practice
        for v in all_vals:
            assert v is None or isinstance(v, (int, float))


class TestSeriesFiltering:
    def test_date_range_reduces_data(self):
        full = _series(cities="Pune", start=START, end=END, metric="pm25_mean").json()
        narrow = _series(cities="Pune", start="2025-06-01", end="2025-06-30", metric="pm25_mean").json()
        assert len(narrow["series"][0]["data"]) < len(full["series"][0]["data"])

    def test_date_inclusive(self):
        body = _series(cities="Pune", start=START, end=START, metric="pm25_mean").json()
        for row in body["series"][0]["data"]:
            assert row["date"] == START

    def test_no_date_filter(self):
        r = _series(cities="Pune", metric="pm25_mean")
        assert r.status_code == 200

    def test_out_of_range_empty(self):
        body = _series(cities="Pune", start="2000-01-01", end="2000-12-31", metric="pm25_mean").json()
        assert body["series"][0]["data"] == []
        assert body["summary"] == []


class TestSeriesErrors:
    def test_unknown_city_404(self):
        assert _series(cities="Atlantis", metric="pm25_mean").status_code == 404

    def test_bad_metric_400(self):
        assert _series(cities="Pune", metric="aqi").status_code == 400

    def test_start_after_end_400(self):
        assert _series(cities="Pune", start="2026-01-01", end="2025-01-01", metric="pm25_mean").status_code == 400

    def test_bad_date_400(self):
        assert _series(cities="Pune", start="not-a-date", metric="pm25_mean").status_code == 400

    def test_missing_cities_422(self):
        assert _series(metric="pm25_mean").status_code == 422


class TestDownload:
    def test_download_returns_csv(self):
        r = _download(cities="Pune", start=START, end=END, metric="pm25_mean")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]

    def test_download_content_disposition(self):
        r = _download(cities="Pune", start=START, end=END, metric="pm25_mean")
        assert "attachment" in r.headers.get("content-disposition", "")

    def test_download_has_header_row(self):
        r = _download(cities="Pune", start=START, end=END, metric="pm25_mean")
        lines = r.text.strip().splitlines()
        header = lines[0].split(",")
        assert "city" in header and "date" in header and "pm25_mean" in header

    def test_download_filters_city(self):
        r = _download(cities="Pune", start=START, end=END, metric="pm25_mean")
        lines = r.text.strip().splitlines()[1:]
        for line in lines:
            assert "Pune" in line

    def test_download_all_cities(self):
        r = _download(cities=["Pune", "Mumbai"], start=START, end=END, metric="pm25_mean")
        assert r.status_code == 200
        text = r.text
        assert "Pune" in text and "Mumbai" in text

    def test_download_unknown_city_404(self):
        assert _download(cities="Atlantis", metric="pm25_mean").status_code == 404
