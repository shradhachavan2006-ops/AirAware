"""Tests for /datasets router."""

from __future__ import annotations

import io
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_list_datasets_endpoint():
    res = client.get("/datasets")
    assert res.status_code == 200
    data = res.json()
    assert "datasets" in data
    assert len(data["datasets"]) >= 4
    ids = [d["id"] for d in data["datasets"]]
    assert "demo:pune" in ids
    assert "demo:mumbai" in ids


def test_get_dataset_info_valid_and_missing():
    res = client.get("/datasets/demo:pune")
    assert res.status_code == 200
    info = res.json()
    assert info["id"] == "demo:pune"
    assert info["is_demo"] is True
    assert info["rows"] > 0
    assert info["date_start"] < info["date_end"]

    res_missing = client.get("/datasets/demo:unknown_city_999")
    assert res_missing.status_code == 404


def test_get_dataset_preview():
    res = client.get("/datasets/demo:pune/preview?rows=5")
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_id"] == "demo:pune"
    assert "date" in data["columns"]
    assert "pm25_mean" in data["columns"]
    assert len(data["rows"]) == 5
    assert data["showing"] == 5

    # Invalid rows parameter (<1 or >200)
    res_invalid = client.get("/datasets/demo:pune/preview?rows=0")
    assert res_invalid.status_code == 400
    res_too_large = client.get("/datasets/demo:pune/preview?rows=500")
    assert res_too_large.status_code == 400


def test_upload_and_delete_lifecycle():
    csv_content = "date,pm25_mean\n" + "\n".join(
        [f"2024-02-{i:02d},{30.0 + i}" for i in range(1, 20)]
    )
    files = {"file": ("test_air.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    data = {"name": "Uploaded Air Test"}

    res = client.post("/datasets/upload", files=files, data=data)
    assert res.status_code == 200
    resp_data = res.json()
    assert "dataset" in resp_data
    ds_id = resp_data["dataset"]["id"]
    assert resp_data["dataset"]["name"] == "Uploaded Air Test"
    assert resp_data["dataset"]["rows"] == 19

    try:
        # Check preview of uploaded dataset
        prev_res = client.get(f"/datasets/{ds_id}/preview?rows=10")
        assert prev_res.status_code == 200
        assert len(prev_res.json()["rows"]) == 10
    finally:
        # Delete dataset
        del_res = client.delete(f"/datasets/{ds_id}")
        assert del_res.status_code == 200

    # Ensure deleted
    del_again = client.delete(f"/datasets/{ds_id}")
    assert del_again.status_code == 404


def test_upload_non_csv_fails():
    files = {"file": ("test.txt", io.BytesIO(b"not,a,csv"), "text/plain")}
    res = client.post("/datasets/upload", files=files, data={"name": "Bad Ext"})
    assert res.status_code == 400


def test_upload_validation_error_fails():
    csv_content = "wrong_col,value\n1,2\n3,4\n"
    files = {"file": ("bad.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/datasets/upload", files=files, data={"name": "Missing Required"})
    assert res.status_code == 422


def test_delete_demo_dataset_fails():
    res = client.delete("/datasets/demo:pune")
    assert res.status_code == 404

