"""Tests for publisher heartbeat monitoring."""

import json

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def utc_timestamp(seconds_ago):
    value = (
        datetime.now(timezone.utc)
        - timedelta(seconds=seconds_ago)
    )

    return value.isoformat().replace("+00:00", "Z")


def create_heartbeat(tmp_path, monkeypatch, age_seconds):
    path = tmp_path / "publisher-health.json"

    data = {
        "schema_version": 1,
        "component": "zeek_publisher",
        "result": "success",
        "last_success_at_utc": utc_timestamp(age_seconds),
        "input_updated_at_utc": utc_timestamp(86400),
        "snapshot_updated_at_utc": utc_timestamp(86400),
        "input_bytes": 2527,
        "snapshot_bytes": 2527,
    }

    path.write_text(
        json.dumps(data),
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "BLUEGUARD_PUBLISHER_HEALTH_FILE",
        str(path),
    )

    return path


@pytest.mark.parametrize(
    "age_seconds,expected",
    [
        (30, "healthy"),
        (400, "stale"),
    ],
)
def test_publisher_freshness(
    tmp_path,
    monkeypatch,
    age_seconds,
    expected,
):
    create_heartbeat(
        tmp_path,
        monkeypatch,
        age_seconds,
    )

    response = client.get(
        "/api/v1/telemetry/publisher"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["publisher_status"] == expected
    assert body["sensor_connectivity"] == "unknown"
    assert body["snapshot_bytes"] == 2527


def test_missing_heartbeat(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "BLUEGUARD_PUBLISHER_HEALTH_FILE",
        str(tmp_path / "missing.json"),
    )

    response = client.get(
        "/api/v1/telemetry/publisher"
    )

    assert response.status_code == 200
    assert (
        response.json()["publisher_status"]
        == "unavailable"
    )


def test_invalid_heartbeat(tmp_path, monkeypatch):
    path = create_heartbeat(
        tmp_path,
        monkeypatch,
        30,
    )

    path.write_text(
        '{"schema_version": 99}',
        encoding="utf-8",
    )

    response = client.get(
        "/api/v1/telemetry/publisher"
    )

    assert response.status_code == 200
    assert (
        response.json()["publisher_status"]
        == "unavailable"
    )


def test_future_heartbeat(tmp_path, monkeypatch):
    create_heartbeat(
        tmp_path,
        monkeypatch,
        -600,
    )

    response = client.get(
        "/api/v1/telemetry/publisher"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["publisher_status"] == "unavailable"
    assert body["reason"] == "timestamp_clock_skew"
