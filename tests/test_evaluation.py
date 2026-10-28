"""Tests for GET /evaluation/cities and GET /evaluation/{city}."""

from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
ALL_CITIES = {"Mumbai", "Nagpur", "Nashik", "Pune"}
MODELS = {"Persistence", "RandomForest"}


class TestCitiesEndpoint:
    def test_200(self):
        assert client.get("/evaluation/cities").status_code == 200

    def test_returns_cities_and_models(self):
        body = client.get("/evaluation/cities").json()
        assert "cities" in body and "models" in body

    def test_all_four_cities_present(self):
        body = client.get("/evaluation/cities").json()
        assert set(body["cities"]) == ALL_CITIES

    def test_models_correct(self):
        body = client.get("/evaluation/cities").json()
        assert set(body["models"]) == MODELS

    def test_persistence_first_in_models(self):
        body = client.get("/evaluation/cities").json()
        assert body["models"][0] == "Persistence"


class TestCityEndpoint:
    @pytest.mark.parametrize("city", sorted(ALL_CITIES))
    def test_each_city_200(self, city):
        assert client.get(f"/evaluation/{city}").status_code == 200

    def test_unknown_city_404(self):
        assert client.get("/evaluation/Atlantis").status_code == 404

    def test_top_level_keys(self):
        body = client.get("/evaluation/Pune").json()
        for k in ("city", "test_window", "metrics", "rf_worse_than_persistence",
                  "chart_data", "prediction_records", "disclaimer"):
            assert k in body

    def test_city_echoed(self):
        assert client.get("/evaluation/Pune").json()["city"] == "Pune"

    def test_disclaimer_present(self):
        d = client.get("/evaluation/Pune").json()["disclaimer"]
        assert isinstance(d, str) and len(d) > 10

    def test_metrics_has_two_models(self):
        metrics = client.get("/evaluation/Pune").json()["metrics"]
        model_names = {m["model"] for m in metrics}
        assert model_names == MODELS

    def test_metrics_persistence_first(self):
        metrics = client.get("/evaluation/Pune").json()["metrics"]
        assert metrics[0]["model"] == "Persistence"

    def test_metrics_has_mae_rmse_r2(self):
        for m in client.get("/evaluation/Pune").json()["metrics"]:
            assert "MAE" in m and "RMSE" in m and "R2" in m

    def test_negative_r2_preserved(self):
        """R² must not be clipped to zero — Mumbai RandomForest has negative R²."""
        body = client.get("/evaluation/Mumbai").json()
        rf = next((m for m in body["metrics"] if m["model"] == "RandomForest"), None)
        assert rf is not None
        assert rf["R2"] < 0, "Mumbai RandomForest R² is known to be negative"

    def test_rf_worse_flag_correct_for_mumbai(self):
        """Mumbai RandomForest MAE > Persistence MAE in the report."""
        body = client.get("/evaluation/Mumbai").json()
        assert body["rf_worse_than_persistence"] is True

    def test_chart_data_keys(self):
        cd = client.get("/evaluation/Pune").json()["chart_data"]
        assert "actual" in cd and "models" in cd

    def test_actual_series_dates_sorted(self):
        actual = client.get("/evaluation/Pune").json()["chart_data"]["actual"]
        dates = [r["date"] for r in actual]
        assert dates == sorted(dates)

    def test_actual_no_duplicate_dates(self):
        actual = client.get("/evaluation/Pune").json()["chart_data"]["actual"]
        dates = [r["date"] for r in actual]
        assert len(dates) == len(set(dates))

    def test_model_series_has_both_models(self):
        models = {m["model"] for m in client.get("/evaluation/Pune").json()["chart_data"]["models"]}
        assert models == MODELS

    def test_prediction_records_keys(self):
        body = client.get("/evaluation/Pune").json()
        for model, rows in body["prediction_records"].items():
            for row in rows:
                for k in ("date", "city", "model", "actual_pm25", "predicted_pm25"):
                    assert k in row

    def test_prediction_records_sorted_newest_first(self):
        body = client.get("/evaluation/Pune").json()
        for model, rows in body["prediction_records"].items():
            dates = [r["date"] for r in rows]
            assert dates == sorted(dates, reverse=True)

    def test_test_window_present(self):
        tw = client.get("/evaluation/Pune").json()["test_window"]
        assert tw is not None
        assert "start" in tw and "end" in tw

    def test_mae_is_positive(self):
        for m in client.get("/evaluation/Pune").json()["metrics"]:
            assert m["MAE"] > 0

    def test_rmse_is_positive(self):
        for m in client.get("/evaluation/Pune").json()["metrics"]:
            assert m["RMSE"] > 0
