"""Evaluate the quality of available Zeek telemetry."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from .telemetry_health import (
    TelemetryHealthResponse,
    get_telemetry_health,
)
from .publisher_health import (
    PublisherHealthResponse,
    get_publisher_health,
)
from .ingestion_health import (
    IngestionHealthResponse,
    ingestion_health,
)


router = APIRouter(
    prefix="/api/v1/telemetry",
    tags=["telemetry"],
)


QualityStatus = Literal[
    "healthy",
    "degraded",
    "critical",
    "unknown",
]

CaptureFidelity = Literal[
    "no_observed_gaps",
    "gaps_observed",
    "unknown",
]


class TelemetryQualityResponse(BaseModel):
    policy_version: Literal[1] = 1

    scope: Literal[
        "available_zeek_snapshot"
    ] = "available_zeek_snapshot"

    quality_status: QualityStatus
    capture_fidelity: CaptureFidelity

    sensor_connectivity: Literal["unknown"] = "unknown"

    reasons: list[str]

    snapshot: TelemetryHealthResponse
    publisher: PublisherHealthResponse
    ingestion: IngestionHealthResponse


def evaluate_quality(
    snapshot: TelemetryHealthResponse,
    publisher: PublisherHealthResponse,
    ingestion: IngestionHealthResponse,
) -> TelemetryQualityResponse:
    """Evaluate existing health assessments without modifying data."""

    reasons: list[str] = []

    critical = False
    degraded = False
    unknown = False

    capture: CaptureFidelity = "unknown"

    # Snapshot freshness.
    if snapshot.data_status == "stale":
        degraded = True
        reasons.append("snapshot_stale")

    elif snapshot.data_status == "unavailable":
        unknown = True
        reasons.append("snapshot_unavailable")

    # Capture fidelity of the available snapshot.
    has_capture_evidence = (
        snapshot.data_status != "unavailable"
        and snapshot.records is not None
        and snapshot.records > 0
        and snapshot.missed_bytes_complete is True
        and snapshot.missed_bytes_total is not None
        and snapshot.missed_bytes_total >= 0
    )

    if has_capture_evidence:
        if snapshot.missed_bytes_total > 0:
            capture = "gaps_observed"
            reasons.append("snapshot_gaps_observed")

            if snapshot.data_status == "fresh":
                critical = True
        else:
            capture = "no_observed_gaps"

    else:
        unknown = True
        reasons.append("capture_evidence_unavailable")

    # Publisher health.
    if publisher.publisher_status == "stale":
        degraded = True
        reasons.append("publisher_stale")

    elif publisher.publisher_status == "unavailable":
        unknown = True
        reasons.append("publisher_unavailable")

    # Ingestion health.
    if ingestion.ingestion_status == "stale":
        degraded = True
        reasons.append("ingestion_stale")

    elif ingestion.ingestion_status == "unavailable":
        unknown = True
        reasons.append("ingestion_unavailable")

    # Deterministic priority:
    # critical > degraded > unknown > healthy.
    status: QualityStatus

    if critical:
        status = "critical"
    elif degraded:
        status = "degraded"
    elif unknown:
        status = "unknown"
    else:
        status = "healthy"

    return TelemetryQualityResponse(
        quality_status=status,
        capture_fidelity=capture,
        reasons=reasons,
        snapshot=snapshot,
        publisher=publisher,
        ingestion=ingestion,
    )


@router.get(
    "/quality",
    response_model=TelemetryQualityResponse,
)
def get_telemetry_quality():
    return evaluate_quality(
        snapshot=get_telemetry_health(),
        publisher=get_publisher_health(),
        ingestion=ingestion_health(),
    )
