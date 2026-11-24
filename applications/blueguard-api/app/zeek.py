"""Read and validate a read-only Zeek conn.log JSONL snapshot."""

import json
import math
import os

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, IPvAnyAddress


DEFAULT_PATH = (
    Path(__file__).resolve().parent.parent
    / "data/zeek/conn-ad05.jsonl"
)

MAX_SNAPSHOT_BYTES = 10 * 1024 * 1024
MAX_RECORDS = 10_000


class ZeekConnection(BaseModel):
    uid: str = Field(min_length=1, max_length=128)
    timestamp_utc: datetime

    source_ip: IPvAnyAddress
    source_port: int = Field(ge=0, le=65535)

    destination_ip: IPvAnyAddress
    destination_port: int = Field(ge=0, le=65535)

    proto: str = Field(min_length=1, max_length=24)
    service: str | None = Field(default=None, max_length=80)

    duration: float | None = Field(
        default=None, ge=0, allow_inf_nan=False
    )

    orig_bytes: int | None = Field(default=None, ge=0)
    resp_bytes: int | None = Field(default=None, ge=0)

    conn_state: str | None = Field(default=None, max_length=32)
    missed_bytes: int | None = Field(default=None, ge=0)

    orig_pkts: int | None = Field(default=None, ge=0)
    resp_pkts: int | None = Field(default=None, ge=0)

    provenance: Literal["zeek_snapshot"] = "zeek_snapshot"


class ZeekConnectionPage(BaseModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)

    source: Literal["zeek_snapshot"] = "zeek_snapshot"
    live: Literal[False] = False

    items: list[ZeekConnection]


def load_zeek_snapshot(path: Path) -> tuple[ZeekConnection, ...]:
    """Load a bounded snapshot; reject malformed records."""

    if path.stat().st_size > MAX_SNAPSHOT_BYTES:
        raise ValueError("Zeek snapshot exceeds 10 MiB")

    events = []
    seen = set()

    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue

            if len(events) >= MAX_RECORDS:
                raise ValueError("Too many Zeek records")

            try:
                raw = json.loads(line)

                if not isinstance(raw, dict):
                    raise ValueError("Expected JSON object")

                ts = raw["ts"]

                if (
                    isinstance(ts, bool)
                    or not isinstance(ts, (int, float))
                    or not math.isfinite(ts)
                ):
                    raise ValueError("Invalid timestamp")

                event = ZeekConnection.model_validate({
                    "uid": raw.get("uid"),
                    "timestamp_utc": datetime.fromtimestamp(
                        ts, tz=timezone.utc
                    ),
                    "source_ip": raw.get("id.orig_h"),
                    "source_port": raw.get("id.orig_p"),
                    "destination_ip": raw.get("id.resp_h"),
                    "destination_port": raw.get("id.resp_p"),
                    "proto": raw.get("proto"),
                    "service": raw.get("service"),
                    "duration": raw.get("duration"),
                    "orig_bytes": raw.get("orig_bytes"),
                    "resp_bytes": raw.get("resp_bytes"),
                    "conn_state": raw.get("conn_state"),
                    "missed_bytes": raw.get("missed_bytes"),
                    "orig_pkts": raw.get("orig_pkts"),
                    "resp_pkts": raw.get("resp_pkts"),
                })

                identity = (event.uid, event.timestamp_utc)

                if identity in seen:
                    raise ValueError("Duplicate Zeek connection")

            except (ValueError, KeyError, TypeError, OverflowError) as exc:
                raise ValueError(
                    f"Invalid Zeek record at line {line_number}"
                ) from exc

            seen.add(identity)
            events.append(event)

    if not events:
        raise ValueError("Zeek snapshot is empty")

    return tuple(sorted(
        events,
        key=lambda event: event.timestamp_utc,
        reverse=True
    ))


@lru_cache(maxsize=1)
def _load_cached_zeek_snapshot(
    filename: str,
    fingerprint: tuple[int, int, int, int, int],
) -> tuple[ZeekConnection, ...]:
    """Cache one immutable generation of the published Zeek file."""
    return load_zeek_snapshot(Path(filename))


def get_zeek_snapshot() -> tuple[ZeekConnection, ...]:
    """Reload Zeek connections when the published file changes."""

    path = Path(os.environ.get(
        "BLUEGUARD_ZEEK_FILE",
        str(DEFAULT_PATH)
    ))

    metadata = path.stat()

    fingerprint = (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )

    return _load_cached_zeek_snapshot(str(path), fingerprint)
