"""Tests for /quality router."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_get_quality_profile_pune():
    res = client.get("/quality/demo:pune")
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_id"] == "demo:pune"
    assert "shape" in data
    assert data["shape"]["rows"] > 0
    assert "columns" in data
    assert any(c["name"] == "pm25_mean" for c in data["columns"])
    assert "outliers" in data
    assert "bounds" in data["outliers"]
    assert "quality_score" in data
    assert 0 <= data["quality_score"] <= 100
    assert "preprocessing_recommendations" in data
    assert isinstance(data["preprocessing_recommendations"], list)


def test_get_quality_profile_not_found():
    res = client.get("/quality/nonexistent_id_404")
    assert res.status_code == 404


def test_download_cleaned_dataset():
    res = client.get("/quality/demo:mumbai/cleaned")
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    lines = res.text.strip().split("\n")
    assert len(lines) > 10
    header = lines[0].split(",")
    assert "date" in header
    assert "pm25_mean" in header


def test_download_cleaned_dataset_not_found():
    res = client.get("/quality/nonexistent_id_404/cleaned")
    assert res.status_code == 404

