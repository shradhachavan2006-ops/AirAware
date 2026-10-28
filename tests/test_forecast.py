"""Tests for GET /forecast/cities and GET /forecast/{city}.

These tests verify:
- The API shape and HTTP status codes.
- That forecast dates are strictly beyond the latest observed date.
- That no historical actual values are fabricated as forecasts.
- That supported horizons produce the correct number of points.
- That forecast engine correctness properties hold (clipping, ordering).
- Error handling for unknown cities and invalid horizons.

NOTE: These tests train per-city RandomForest models, which takes a few
seconds. The model cache prevents redundant training across tests.
"""

from __future__ import annotations

import datetime

import pytest
from fastapi.testclient import TestClient

from backend.data_loader import load_daily_data
from backend.main import app

client = TestClient(app)
ALL_CITIES = {"Mumbai", "Nagpur", "Nashik", "Pune"}
HORIZONS = (7, 14)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def latest_dates() -> dict[str, datetime.date]:
    """Return the latest observed date per city from the real dataset."""
    df = load_daily_data()
    result: dict[str, datetime.date] = {}
    for city, grp in df.groupby("city"):
        valid = grp.dropna(subset=["pm25_mean"])
        if not valid.empty:
            result[str(city)] = valid["date"].max().date()
    return result


# ── /forecast/cities ─────────────────────────────────────────────────────────

class TestForecastCitiesEndpoint:
    def test_200(self):
        assert client.get("/forecast/cities").status_code == 200

    def test_shape(self):
        body = client.get("/forecast/cities").json()
        for key in ("cities", "max_horizon", "supported_horizons", "model", "note"):
            assert key in body, f"Missing key: {key}"

    def test_all_cities_available(self):
        body = client.get("/forecast/cities").json()
        assert set(body["cities"]) == ALL_CITIES

    def test_max_horizon_is_14(self):
        body = client.get("/forecast/cities").json()
        assert body["max_horizon"] == 14

    def test_supported_horizons(self):
        body = client.get("/forecast/cities").json()
        assert set(body["supported_horizons"]) == {7, 14}

    def test_model_is_randomforest(self):
        body = client.get("/forecast/cities").json()
        assert "RandomForest" in body["model"]

    def test_cities_sorted(self):
        body = client.get("/forecast/cities").json()
        cities = body["cities"]
        assert cities == sorted(cities)


# ── /forecast/{city} ─────────────────────────────────────────────────────────

class TestForecastCityEndpoint:
    @pytest.mark.parametrize("city", sorted(ALL_CITIES))
    def test_each_city_200(self, city):
        assert client.get(f"/forecast/{city}?horizon=7").status_code == 200

    def test_unknown_city_404(self):
        assert client.get("/forecast/Atlantis?horizon=7").status_code == 404

    def test_invalid_horizon_400(self):
        assert client.get("/forecast/Pune?horizon=3").status_code == 400

    def test_horizon_1_rejected(self):
        assert client.get("/forecast/Pune?horizon=1").status_code == 400

    def test_horizon_15_rejected(self):
        assert client.get("/forecast/Pune?horizon=15").status_code in (400, 422)

    def test_top_level_keys(self):
        body = client.get("/forecast/Pune?horizon=7").json()
        for key in (
            "city", "horizon", "latest_observed_date", "latest_observed_pm25",
            "historical_tail", "forecast", "chart_series",
            "train_rows", "feature_importance", "model_note", "disclaimer",
        ):
            assert key in body, f"Missing key: {key}"

    def test_city_echoed(self):
        assert client.get("/forecast/Pune?horizon=7").json()["city"] == "Pune"

    def test_horizon_echoed_7(self):
        assert client.get("/forecast/Pune?horizon=7").json()["horizon"] == 7

    def test_horizon_echoed_14(self):
        assert client.get("/forecast/Pune?horizon=14").json()["horizon"] == 14

    @pytest.mark.parametrize("horizon", HORIZONS)
    def test_forecast_length_matches_horizon(self, horizon):
        body = client.get(f"/forecast/Pune?horizon={horizon}").json()
        assert len(body["forecast"]) == horizon, (
            f"Expected {horizon} forecast points, got {len(body['forecast'])}"
        )

    @pytest.mark.parametrize("city", sorted(ALL_CITIES))
    def test_forecast_7day_all_cities(self, city):
        body = client.get(f"/forecast/{city}?horizon=7").json()
        assert len(body["forecast"]) == 7

    def test_forecast_dates_are_strictly_future(self, latest_dates):
        """Forecast dates must all be after the latest observed date."""
        for city in ALL_CITIES:
            body = client.get(f"/forecast/{city}?horizon=7").json()
            latest = latest_dates.get(city)
            if latest is None:
                continue
            for pt in body["forecast"]:
                pt_date = datetime.date.fromisoformat(pt["date"])
                assert pt_date > latest, (
                    f"{city}: forecast date {pt_date} is not after latest observed {latest}"
                )

    def test_forecast_starts_day_after_latest(self, latest_dates):
        """The first forecast date must be exactly latest_observed_date + 1."""
        for city in ALL_CITIES:
            body = client.get(f"/forecast/{city}?horizon=7").json()
            latest = latest_dates.get(city)
            if latest is None:
                continue
            first_forecast = datetime.date.fromisoformat(body["forecast"][0]["date"])
            assert first_forecast == latest + datetime.timedelta(days=1), (
                f"{city}: expected first forecast {latest + datetime.timedelta(days=1)}, "
                f"got {first_forecast}"
            )

    def test_forecast_dates_sequential(self):
        """Forecast dates must be consecutive calendar days."""
        body = client.get("/forecast/Pune?horizon=7").json()
        dates = [datetime.date.fromisoformat(pt["date"]) for pt in body["forecast"]]
        for i in range(1, len(dates)):
            assert dates[i] == dates[i - 1] + datetime.timedelta(days=1), (
                f"Non-consecutive dates at index {i}: {dates[i-1]} → {dates[i]}"
            )

    def test_horizon_days_are_1_indexed(self):
        body = client.get("/forecast/Pune?horizon=7").json()
        horizons = [pt["horizon_day"] for pt in body["forecast"]]
        assert horizons == list(range(1, 8))

    def test_predicted_values_non_negative(self):
        """RF predictions are clipped to [0, 999]; all should be >= 0."""
        for city in ALL_CITIES:
            body = client.get(f"/forecast/{city}?horizon=7").json()
            for pt in body["forecast"]:
                assert pt["predicted_pm25"] >= 0.0, (
                    f"{city}: negative prediction {pt['predicted_pm25']} on {pt['date']}"
                )

    def test_predicted_values_below_cap(self):
        for city in ALL_CITIES:
            body = client.get(f"/forecast/{city}?horizon=7").json()
            for pt in body["forecast"]:
                assert pt["predicted_pm25"] <= 999.0

    def test_forecast_point_keys(self):
        body = client.get("/forecast/Pune?horizon=7").json()
        for pt in body["forecast"]:
            for k in ("date", "predicted_pm25", "horizon_day"):
                assert k in pt

    def test_historical_tail_is_not_empty(self):
        body = client.get("/forecast/Pune?horizon=7").json()
        assert len(body["historical_tail"]) > 0

    def test_historical_tail_is_not_forecast(self):
        """Historical tail points must all have is_forecast=False."""
        body = client.get("/forecast/Pune?horizon=7").json()
        for pt in body["historical_tail"]:
            assert pt["is_forecast"] is False

    def test_chart_series_forecast_points_marked(self):
        """chart_series forecast points must have is_forecast=True."""
        body = client.get("/forecast/Pune?horizon=7").json()
        forecast_pts = [p for p in body["chart_series"] if p["is_forecast"]]
        assert len(forecast_pts) == 7

    def test_chart_series_no_overlap_with_history(self, latest_dates):
        """No chart_series date that is_forecast=True should be <= latest observed date."""
        for city in ALL_CITIES:
            body = client.get(f"/forecast/{city}?horizon=7").json()
            latest = latest_dates.get(city)
            if latest is None:
                continue
            for pt in body["chart_series"]:
                if pt["is_forecast"]:
                    pt_date = datetime.date.fromisoformat(pt["date"])
                    assert pt_date > latest

    def test_latest_observed_date_format(self):
        body = client.get("/forecast/Pune?horizon=7").json()
        # Must parse as a valid ISO date
        datetime.date.fromisoformat(body["latest_observed_date"])

    def test_latest_observed_pm25_positive(self):
        body = client.get("/forecast/Pune?horizon=7").json()
        lp = body["latest_observed_pm25"]
        if lp is not None:
            assert lp > 0

    def test_train_rows_positive(self):
        body = client.get("/forecast/Pune?horizon=7").json()
        assert body["train_rows"] > 0

    def test_feature_importance_keys(self):
        body = client.get("/forecast/Pune?horizon=7").json()
        fi = body["feature_importance"]
        for feat in (
            "pm25_today", "pm25_lag1", "pm25_lag2", "pm25_lag3",
            "pm25_lag7", "rolling_mean_3", "rolling_mean_7",
        ):
            assert feat in fi

    def test_feature_importance_sums_to_approx_1(self):
        body = client.get("/forecast/Pune?horizon=7").json()
        total = sum(body["feature_importance"].values())
        assert abs(total - 1.0) < 0.05

    def test_disclaimer_present(self):
        body = client.get("/forecast/Pune?horizon=7").json()
        assert isinstance(body["disclaimer"], str) and len(body["disclaimer"]) > 20

    def test_model_note_mentions_training(self):
        body = client.get("/forecast/Pune?horizon=7").json()
        assert "trained" in body["model_note"].lower()

    def test_default_horizon_is_7(self):
        """Omitting horizon should default to 7 days."""
        body = client.get("/forecast/Pune").json()
        assert body["horizon"] == 7

    def test_14_day_more_points_than_7(self):
        body7  = client.get("/forecast/Pune?horizon=7").json()
        body14 = client.get("/forecast/Pune?horizon=14").json()
        assert len(body14["forecast"]) > len(body7["forecast"])


# ── /forecast/{city}/download ─────────────────────────────────────────────────

class TestForecastDownload:
    def test_download_200(self):
        assert client.get("/forecast/Pune/download?horizon=7").status_code == 200

    def test_download_content_type(self):
        res = client.get("/forecast/Pune/download?horizon=7")
        assert "text/csv" in res.headers.get("content-type", "")

    def test_download_disposition(self):
        res = client.get("/forecast/Pune/download?horizon=7")
        cd = res.headers.get("content-disposition", "")
        assert "attachment" in cd and ".csv" in cd

    def test_download_has_header_row(self):
        res = client.get("/forecast/Pune/download?horizon=7")
        lines = res.text.strip().splitlines()
        header = lines[0].lower()
        for col in ("city", "target_date", "predicted_pm25", "horizon_day"):
            assert col in header

    def test_download_row_count(self):
        """CSV body should have 7 data rows + 1 header row."""
        res = client.get("/forecast/Pune/download?horizon=7")
        lines = [l for l in res.text.strip().splitlines() if l]
        assert len(lines) == 8  # 1 header + 7 data rows

    def test_download_14day_row_count(self):
        res = client.get("/forecast/Pune/download?horizon=14")
        lines = [l for l in res.text.strip().splitlines() if l]
        assert len(lines) == 15  # 1 header + 14 data rows

    def test_download_unknown_city_404(self):
        assert client.get("/forecast/Atlantis/download?horizon=7").status_code == 404

    def test_download_bad_horizon_400(self):
        assert client.get("/forecast/Pune/download?horizon=3").status_code == 400
