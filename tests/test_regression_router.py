"""Tests for /analysis/{dataset_id}/regression router."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_get_regression_analysis_pune():
    res = client.get("/analysis/demo:pune/regression")
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_id"] == "demo:pune"
    assert "n_samples" in data
    assert data["n_samples"] > 10
    assert "target" in data
    assert "correlation" in data
    assert "lag_1" in data["correlation"]
    assert "r" in data["correlation"]["lag_1"]

    assert "simple_regression" in data
    slr = data["simple_regression"]
    assert slr["feature"] == "lag_1"
    assert "slope" in slr
    assert "intercept" in slr
    assert "r_squared" in slr
    assert len(slr["scatter_data"]) > 0
    assert len(slr["residual_data"]) > 0

    assert "multiple_regression" in data
    mlr = data["multiple_regression"]
    assert "r_squared" in mlr
    assert "adjusted_r_squared" in mlr
    assert "coefficients" in mlr
    assert len(mlr["coefficients"]) >= 3
    assert len(mlr["actual_vs_predicted"]) > 0


def test_get_regression_analysis_not_found():
    res = client.get("/analysis/nonexistent_dataset/regression")
    assert res.status_code == 404

