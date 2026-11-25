"""Read-only monitoring of validated Zeek ingestion receipts."""

import json
import os
import stat

from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(
    prefix="/api/v1/telemetry",
    tags=["telemetry"],
)

DEFAULT_FILE = "/app/data/zeek/ingestion-health.json"

THRESHOLD_SECONDS = 900
FUTURE_TOLERANCE_SECONDS = 60
MAX_FILE_BYTES = 4096
MAX_RECORDS = 10000


class IngestionHealthResponse(BaseModel):
    ingestion_status: Literal[
        "recent", "stale", "unavailable"
    ]

    freshness_threshold_seconds: int = THRESHOLD_SECONDS
    sensor_connectivity: Literal["unknown"] = "unknown"

    last_valid_batch_at_utc: datetime | None = None
    last_valid_batch_age_seconds: int | None = None

    store_updated_at_utc: datetime | None = None
    store_age_seconds: int | None = None

    last_batch_new_records: int | None = None
    last_batch_duplicate_records: int | None = None
    total_records_after_batch: int | None = None

    reason: str | None = None


def parse_utc(value):
    if (
        not isinstance(value, str)
        or not value.endswith("Z")
        or len(value) > 40
    ):
        raise ValueError("Invalid UTC timestamp")

    parsed = datetime.fromisoformat(
        value[:-1] + "+00:00"
    )

    if parsed.utcoffset() != timedelta(0):
        raise ValueError("Timestamp is not UTC")

    return parsed


def read_receipt(path):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)

    fd = os.open(path, flags)

    try:
        info = os.fstat(fd)

        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Receipt is not a regular file")

        if info.st_nlink != 1:
            raise ValueError("Unexpected receipt hard links")

        if not 0 < info.st_size <= MAX_FILE_BYTES:
            raise ValueError("Invalid receipt size")

        raw = os.read(fd, MAX_FILE_BYTES + 1)

        if not 0 < len(raw) <= MAX_FILE_BYTES:
            raise ValueError("Invalid receipt contents")

    finally:
        os.close(fd)

    return json.loads(raw)


def validate_receipt(data):
    if not isinstance(data, dict):
        raise ValueError("Invalid receipt structure")

    if (
        type(data.get("schema_version")) is not int
        or data["schema_version"] != 1
        or data.get("component") != "zeek_ingestion"
        or data.get("result") != "success"
    ):
        raise ValueError("Invalid receipt schema")

    batch_time = parse_utc(
        data.get("last_valid_batch_at_utc")
    )

    store_time = parse_utc(
        data.get("store_updated_at_utc")
    )

    now = datetime.now(timezone.utc)

    if batch_time > now + timedelta(
        seconds=FUTURE_TOLERANCE_SECONDS
    ):
        return None, "timestamp_clock_skew"

    if store_time > now + timedelta(
        seconds=FUTURE_TOLERANCE_SECONDS
    ):
        return None, "timestamp_clock_skew"

    if store_time > batch_time + timedelta(
        seconds=FUTURE_TOLERANCE_SECONDS
    ):
        raise ValueError("Inconsistent receipt timestamps")

    fields = (
        "last_batch_new_records",
        "last_batch_duplicate_records",
        "total_records_after_batch",
    )

    for field in fields:
        value = data.get(field)

        if type(value) is not int:
            raise ValueError(f"Invalid counter: {field}")

        if not 0 <= value <= MAX_RECORDS:
            raise ValueError(f"Counter outside limits: {field}")

    new = data["last_batch_new_records"]
    duplicates = data["last_batch_duplicate_records"]
    total = data["total_records_after_batch"]

    if new + duplicates < 1 or new > total:
        raise ValueError("Inconsistent counters")

    batch_age = max(
        0,
        int((now - batch_time).total_seconds()),
    )

    store_age = max(
        0,
        int((now - store_time).total_seconds()),
    )

    status = (
        "recent"
        if batch_age <= THRESHOLD_SECONDS
        else "stale"
    )

    result = IngestionHealthResponse(
        ingestion_status=status,
        last_valid_batch_at_utc=batch_time,
        last_valid_batch_age_seconds=batch_age,
        store_updated_at_utc=store_time,
        store_age_seconds=store_age,
        last_batch_new_records=new,
        last_batch_duplicate_records=duplicates,
        total_records_after_batch=total,
        reason=(
            "recent_accepted_batch"
            if status == "recent"
            else "last_valid_batch_outdated"
        ),
    )

    return result, None


@router.get(
    "/ingestion",
    response_model=IngestionHealthResponse,
)
def ingestion_health():
    path = os.environ.get(
        "BLUEGUARD_INGESTION_HEALTH_FILE",
        DEFAULT_FILE,
    )

    try:
        receipt = read_receipt(path)
        result, error = validate_receipt(receipt)

        if error is not None:
            return IngestionHealthResponse(
                ingestion_status="unavailable",
                reason=error,
            )

        return result

    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        UnicodeError,
    ):
        return IngestionHealthResponse(
            ingestion_status="unavailable",
            reason="receipt_missing_or_invalid",
        )
