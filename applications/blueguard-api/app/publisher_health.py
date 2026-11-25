"""Read-only monitoring of the Zeek publisher heartbeat."""

import json
import os
import stat

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(
    prefix="/api/v1/telemetry",
    tags=["telemetry"],
)

DEFAULT_FILE = "/app/data/zeek/publisher-health.json"

THRESHOLD_SECONDS = 300
FUTURE_TOLERANCE_SECONDS = 60
MAX_FILE_BYTES = 4096


class PublisherHealthResponse(BaseModel):
    publisher_status: Literal[
        "healthy", "stale", "unavailable"
    ]

    threshold_seconds: int = THRESHOLD_SECONDS
    sensor_connectivity: Literal["unknown"] = "unknown"

    last_success_at_utc: datetime | None = None
    last_success_age_seconds: int | None = None

    input_updated_at_utc: datetime | None = None
    snapshot_updated_at_utc: datetime | None = None

    input_bytes: int | None = None
    snapshot_bytes: int | None = None

    reason: str | None = None


def parse_utc(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("Expected UTC timestamp")

    result = datetime.fromisoformat(
        value[:-1] + "+00:00"
    )

    if result.utcoffset() != timedelta(0):
        raise ValueError("Timestamp must be UTC")

    return result


def read_heartbeat():
    path = Path(
        os.environ.get(
            "BLUEGUARD_PUBLISHER_HEALTH_FILE",
            DEFAULT_FILE,
        )
    )

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)

    fd = os.open(path, flags)

    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())

        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Heartbeat is not a regular file")

        if info.st_size > MAX_FILE_BYTES:
            raise ValueError("Heartbeat exceeds size limit")

        content = stream.read(MAX_FILE_BYTES + 1)

    if len(content) > MAX_FILE_BYTES:
        raise ValueError("Heartbeat exceeds size limit")

    data = json.loads(content)

    if not isinstance(data, dict):
        raise ValueError("Invalid heartbeat JSON")

    if (
        type(data.get("schema_version")) is not int
        or data["schema_version"] != 1
        or data.get("component") != "zeek_publisher"
        or data.get("result") != "success"
    ):
        raise ValueError("Invalid heartbeat schema")

    for field in ("input_bytes", "snapshot_bytes"):
        value = data.get(field)

        if (
            type(value) is not int
            or not 0 < value <= 10 * 1024 * 1024
        ):
            raise ValueError("Invalid heartbeat size")

    return data


@router.get(
    "/publisher",
    response_model=PublisherHealthResponse,
)
def get_publisher_health():
    try:
        data = read_heartbeat()

        last_success = parse_utc(
            data["last_success_at_utc"]
        )
        input_updated = parse_utc(
            data["input_updated_at_utc"]
        )
        snapshot_updated = parse_utc(
            data["snapshot_updated_at_utc"]
        )

    except (OSError, ValueError, KeyError, TypeError):
        return PublisherHealthResponse(
            publisher_status="unavailable",
            reason="heartbeat_missing_or_invalid",
        )

    now = datetime.now(timezone.utc)
    tolerance = timedelta(
        seconds=FUTURE_TOLERANCE_SECONDS
    )

    if any(
        timestamp > now + tolerance
        for timestamp in (
            last_success,
            input_updated,
            snapshot_updated,
        )
    ):
        return PublisherHealthResponse(
            publisher_status="unavailable",
            reason="timestamp_clock_skew",
        )

    age = max(
        0,
        int((now - last_success).total_seconds()),
    )

    is_healthy = age <= THRESHOLD_SECONDS

    return PublisherHealthResponse(
        publisher_status=(
            "healthy" if is_healthy else "stale"
        ),
        last_success_at_utc=last_success,
        last_success_age_seconds=age,
        input_updated_at_utc=input_updated,
        snapshot_updated_at_utc=snapshot_updated,
        input_bytes=data["input_bytes"],
        snapshot_bytes=data["snapshot_bytes"],
        reason=(
            "recent_success"
            if is_healthy
            else "last_success_outdated"
        ),
    )
