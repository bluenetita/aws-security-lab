"""Tests for the Zeek ingestion health endpoint."""

import json

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

ENDPOINT = "/api/v1/telemetry/ingestion"
ENV_NAME = "BLUEGUARD_INGESTION_HEALTH_FILE"


def utc(value):
    return value.isoformat().replace("+00:00", "Z")


def sample_receipt(age_seconds=30):
    now = datetime.now(timezone.utc)
    batch_time = now - timedelta(seconds=age_seconds)
    store_time = batch_time - timedelta(hours=3)

    return {
        "schema_version": 1,
        "component": "zeek_ingestion",
        "result": "success",
        "last_valid_batch_at_utc": utc(batch_time),
        "store_updated_at_utc": utc(store_time),
        "last_batch_new_records": 0,
        "last_batch_duplicate_records": 2,
        "total_records_after_batch": 6,
    }


def request_with_receipt(tmp_path, monkeypatch, data):
    path = tmp_path / "ingestion-health.json"

    if isinstance(data, dict):
        path.write_text(
            json.dumps(data),
            encoding="utf-8",
        )
    else:
        path.write_text(data, encoding="utf-8")

    monkeypatch.setenv(ENV_NAME, str(path))

    return client.get(ENDPOINT)


def test_recent_duplicate_only_batch(tmp_path, monkeypatch):
    response = request_with_receipt(
        tmp_path,
        monkeypatch,
        sample_receipt(30),
    )

    assert response.status_code == 200

    body = response.json()

    assert body["ingestion_status"] == "recent"
    assert body["sensor_connectivity"] == "unknown"
    assert body["last_batch_new_records"] == 0
    assert body["last_batch_duplicate_records"] == 2
    assert body["total_records_after_batch"] == 6
    assert body["store_age_seconds"] > 900
    assert body["reason"] == "recent_accepted_batch"


def test_stale_batch(tmp_path, monkeypatch):
    response = request_with_receipt(
        tmp_path,
        monkeypatch,
        sample_receipt(3600),
    )

    body = response.json()

    assert response.status_code == 200
    assert body["ingestion_status"] == "stale"
    assert body["reason"] == "last_valid_batch_outdated"


def test_missing_receipt(tmp_path, monkeypatch):
    path = tmp_path / "missing.json"

    monkeypatch.setenv(ENV_NAME, str(path))

    response = client.get(ENDPOINT)
    body = response.json()

    assert response.status_code == 200
    assert body["ingestion_status"] == "unavailable"
    assert body["reason"] == "receipt_missing_or_invalid"


def test_invalid_schema(tmp_path, monkeypatch):
    data = sample_receipt()
    data["schema_version"] = 2

    body = request_with_receipt(
        tmp_path,
        monkeypatch,
        data,
    ).json()

    assert body["ingestion_status"] == "unavailable"


def test_future_timestamp(tmp_path, monkeypatch):
    data = sample_receipt(-300)

    body = request_with_receipt(
        tmp_path,
        monkeypatch,
        data,
    ).json()

    assert body["ingestion_status"] == "unavailable"
    assert body["reason"] == "timestamp_clock_skew"


def test_invalid_counters(tmp_path, monkeypatch):
    data = sample_receipt()
    data["last_batch_new_records"] = 7
    data["total_records_after_batch"] = 6

    body = request_with_receipt(
        tmp_path,
        monkeypatch,
        data,
    ).json()

    assert body["ingestion_status"] == "unavailable"


def test_invalid_json(tmp_path, monkeypatch):
    body = request_with_receipt(
        tmp_path,
        monkeypatch,
        "{invalid json",
    ).json()

    assert body["ingestion_status"] == "unavailable"


def test_symlink_receipt_rejected(tmp_path, monkeypatch):
    real = tmp_path / "real.json"
    link = tmp_path / "ingestion-health.json"

    real.write_text(
        json.dumps(sample_receipt()),
        encoding="utf-8",
    )

    link.symlink_to(real)

    monkeypatch.setenv(ENV_NAME, str(link))

    response = client.get(ENDPOINT)

    assert response.status_code == 200
    assert response.json()["ingestion_status"] == "unavailable"
