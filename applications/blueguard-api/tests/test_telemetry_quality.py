import pytest

from fastapi.testclient import TestClient

import app.telemetry_quality as quality

from app.main import app
from app.telemetry_health import TelemetryHealthResponse
from app.publisher_health import PublisherHealthResponse
from app.ingestion_health import IngestionHealthResponse


@pytest.mark.parametrize(
    (
        "snapshot_status",
        "records",
        "complete",
        "missed",
        "publisher_status",
        "ingestion_status",
        "expected_status",
        "expected_capture",
    ),
    [
        # Healthy telemetry.
        ("fresh", 5, True, 0, "healthy", "recent",
         "healthy", "no_observed_gaps"),

        # Fresh snapshot with observed gaps.
        ("fresh", 5, True, 134235, "healthy", "recent",
         "critical", "gaps_observed"),

        # Critical takes priority over other conditions.
        ("fresh", 5, True, 134235, "unavailable", "stale",
         "critical", "gaps_observed"),

        # Historical gaps in a stale snapshot.
        ("stale", 5, True, 134235, "healthy", "recent",
         "degraded", "gaps_observed"),

        # Stale snapshot without observed gaps.
        ("stale", 5, True, 0, "healthy", "recent",
         "degraded", "no_observed_gaps"),

        # Stale publisher.
        ("fresh", 5, True, 0, "stale", "recent",
         "degraded", "no_observed_gaps"),

        # Stale ingestion.
        ("fresh", 5, True, 0, "healthy", "stale",
         "degraded", "no_observed_gaps"),

        # Missing snapshot.
        ("unavailable", None, None, None, "healthy", "recent",
         "unknown", "unknown"),

        # Incomplete capture evidence.
        ("fresh", 5, False, None, "healthy", "recent",
         "unknown", "unknown"),

        # Empty snapshot must not imply healthy capture.
        ("fresh", 0, True, 0, "healthy", "recent",
         "unknown", "unknown"),

        # Missing publisher evidence.
        ("fresh", 5, True, 0, "unavailable", "recent",
         "unknown", "no_observed_gaps"),

        # Missing ingestion evidence.
        ("fresh", 5, True, 0, "healthy", "unavailable",
         "unknown", "no_observed_gaps"),

        # Degraded takes priority over unknown.
        ("fresh", 5, False, None, "stale", "recent",
         "degraded", "unknown"),
    ],
)
def test_quality_policy(
    snapshot_status,
    records,
    complete,
    missed,
    publisher_status,
    ingestion_status,
    expected_status,
    expected_capture,
):
    result = quality.evaluate_quality(
        snapshot=TelemetryHealthResponse(
            data_status=snapshot_status,
            records=records,
            missed_bytes_complete=complete,
            missed_bytes_total=missed,
        ),
        publisher=PublisherHealthResponse(
            publisher_status=publisher_status,
        ),
        ingestion=IngestionHealthResponse(
            ingestion_status=ingestion_status,
        ),
    )

    assert result.quality_status == expected_status
    assert result.capture_fidelity == expected_capture
    assert result.sensor_connectivity == "unknown"
    assert result.policy_version == 1

    if expected_status == "healthy":
        assert result.reasons == []
    else:
        assert result.reasons


def test_quality_endpoint(monkeypatch):
    monkeypatch.setattr(
        quality,
        "get_telemetry_health",
        lambda: TelemetryHealthResponse(
            data_status="fresh",
            records=5,
            missed_bytes_complete=True,
            missed_bytes_total=134235,
        ),
    )

    monkeypatch.setattr(
        quality,
        "get_publisher_health",
        lambda: PublisherHealthResponse(
            publisher_status="unavailable",
        ),
    )

    monkeypatch.setattr(
        quality,
        "ingestion_health",
        lambda: IngestionHealthResponse(
            ingestion_status="recent",
        ),
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/telemetry/quality"
        )

    assert response.status_code == 200

    data = response.json()

    assert data["quality_status"] == "critical"
    assert data["capture_fidelity"] == "gaps_observed"

    assert data["reasons"] == [
        "snapshot_gaps_observed",
        "publisher_unavailable",
    ]

    assert data["snapshot"]["missed_bytes_total"] == 134235
    assert data["sensor_connectivity"] == "unknown"
    assert response.headers["Cache-Control"] == "no-store"
