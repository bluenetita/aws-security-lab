"""Regression tests for Zeek telemetry freshness."""

import json
import os
import time

import pytest

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def create_snapshot(tmp_path, monkeypatch, age_seconds):
    now = time.time()
    timestamp = now - age_seconds

    event = {
        "ts": timestamp,
        "uid": "C-telemetry-test",
        "id.orig_h": "10.20.1.11",
        "id.orig_p": 34588,
        "id.resp_h": "10.20.1.10",
        "id.resp_p": 18080,
        "proto": "tcp",
        "service": "http",
        "duration": 1.0,
        "orig_bytes": 1024,
        "resp_bytes": 256,
        "missed_bytes": 0,
        "conn_state": "SF",
    }

    path = tmp_path / "conn.jsonl"
    path.write_text(
        json.dumps(event) + "\n",
        encoding="utf-8",
    )

    os.utime(path, (timestamp, timestamp))

    monkeypatch.setenv(
        "BLUEGUARD_ZEEK_FILE",
        str(path),
    )


@pytest.mark.parametrize(
    "age_seconds,expected",
    [
        (30, "fresh"),
        (3600, "stale"),
    ],
)
def test_snapshot_freshness(
    tmp_path,
    monkeypatch,
    age_seconds,
    expected,
):
    create_snapshot(tmp_path, monkeypatch, age_seconds)

    response = client.get("/api/v1/telemetry/health")

    assert response.status_code == 200

    body = response.json()

    assert body["data_status"] == expected
    assert body["records"] == 1
    assert body["sensor_connectivity"] == "unknown"
    assert body["missed_bytes_total"] == 0


def test_missing_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "BLUEGUARD_ZEEK_FILE",
        str(tmp_path / "missing.jsonl"),
    )

    response = client.get("/api/v1/telemetry/health")

    assert response.status_code == 200
    assert response.json()["data_status"] == "unavailable"


def test_invalid_snapshot(tmp_path, monkeypatch):
    path = tmp_path / "invalid.jsonl"
    path.write_text("{broken json}\n", encoding="utf-8")

    monkeypatch.setenv("BLUEGUARD_ZEEK_FILE", str(path))

    response = client.get("/api/v1/telemetry/health")

    assert response.status_code == 200
    assert response.json()["data_status"] == "unavailable"
