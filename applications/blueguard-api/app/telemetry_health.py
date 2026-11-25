"""Telemetry freshness reporting for the Zeek snapshot."""

import logging
import os

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from .zeek import DEFAULT_PATH, get_zeek_snapshot


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/telemetry",
    tags=["telemetry"],
)

# Laboratory threshold, not evidence that the sensor is down.
FRESHNESS_THRESHOLD_SECONDS = 900


class TelemetryHealthResponse(BaseModel):
    source: Literal["zeek_snapshot"] = "zeek_snapshot"
    ingestion_mode: Literal["periodic_snapshot"] = "periodic_snapshot"
    sensor_connectivity: Literal["unknown"] = "unknown"

    data_status: Literal[
        "fresh", "stale", "unavailable"
    ]

    freshness_threshold_seconds: int = FRESHNESS_THRESHOLD_SECONDS

    records: int | None = None

    snapshot_updated_at_utc: datetime | None = None
    snapshot_age_seconds: int | None = None

    latest_event_at_utc: datetime | None = None
    latest_event_age_seconds: int | None = None

    missed_bytes_total: int | None = None
    missed_bytes_complete: bool | None = None

    reason: str | None = None


@router.get("/health", response_model=TelemetryHealthResponse)
def get_telemetry_health() -> TelemetryHealthResponse:

    path = Path(
        os.environ.get(
            "BLUEGUARD_ZEEK_FILE",
            str(DEFAULT_PATH),
        )
    )

    now = datetime.now(timezone.utc)

    try:
        metadata = path.stat()
        records = get_zeek_snapshot()

        updated_at = datetime.fromtimestamp(
            metadata.st_mtime,
            tz=timezone.utc,
        )

        latest_event = max(
            record.timestamp_utc for record in records
        )

    except (OSError, ValueError, OverflowError) as exc:
        logger.warning(
            "Zeek telemetry unavailable: %s",
            type(exc).__name__,
        )

        return TelemetryHealthResponse(
            data_status="unavailable",
            reason="snapshot_missing_or_invalid",
        )

    snapshot_age = (
        now - updated_at
    ).total_seconds()

    event_age = (
        now - latest_event
    ).total_seconds()

    clock_skew = (
        snapshot_age < -60
        or event_age < -60
    )

    stale = (
        snapshot_age > FRESHNESS_THRESHOLD_SECONDS
        or event_age > FRESHNESS_THRESHOLD_SECONDS
        or clock_skew
    )

    missed_bytes_complete = all(
        record.missed_bytes is not None
        for record in records
    )

    missed_bytes_total = (
        sum(record.missed_bytes for record in records)
        if missed_bytes_complete
        else None
    )

    return TelemetryHealthResponse(
        data_status="stale" if stale else "fresh",
        records=len(records),
        snapshot_updated_at_utc=updated_at,
        snapshot_age_seconds=max(0, int(snapshot_age)),
        latest_event_at_utc=latest_event,
        latest_event_age_seconds=max(0, int(event_age)),
        missed_bytes_total=missed_bytes_total,
        missed_bytes_complete=missed_bytes_complete,
        reason=(
            "timestamp_clock_skew"
            if clock_skew
            else "snapshot_or_events_outdated"
            if stale
            else None
        ),
    )
