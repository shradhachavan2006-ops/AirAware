"""Tests for /analysis/{dataset_id}/statistics router."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_get_statistics_analysis_pune():
    res = client.get("/analysis/demo:pune/statistics")
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_id"] == "demo:pune"
    assert "descriptive" in data
    assert data["descriptive"]["n"] > 0
    assert "mean" in data["descriptive"]
    assert "std" in data["descriptive"]
    assert "normality" in data
    assert "statistic" in data["normality"]
    assert "ttest_who_annual" in data
    assert "t_statistic" in data["ttest_who_annual"]
    assert "ttest_india_naaqs" in data
    assert "confidence_interval_95" in data
    assert data["confidence_interval_95"]["lower"] < data["confidence_interval_95"]["upper"]
    assert "seasonal_anova" in data
    assert "histogram" in data
    assert len(data["histogram"]["bins"]) > 0
    assert len(data["histogram"]["counts"]) == len(data["histogram"]["bins"]) - 1


def test_get_statistics_analysis_not_found():
    res = client.get("/analysis/nonexistent_dataset/statistics")
    assert res.status_code == 404
