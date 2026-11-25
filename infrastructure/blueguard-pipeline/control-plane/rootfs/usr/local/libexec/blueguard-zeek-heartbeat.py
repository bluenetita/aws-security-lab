#!/usr/bin/env python3
"""Publish a heartbeat only after a successful Zeek publisher run."""

import json
import os
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SOURCE = Path("/var/lib/blueguard-ingest/incoming/conn.jsonl")
SNAPSHOT = Path("/var/lib/blueguard/zeek/conn-ingested.jsonl")
HEARTBEAT = Path("/var/lib/blueguard/zeek/publisher-health.json")

POD_GID = 10001


def utc_time(timestamp):
    return (
        datetime.fromtimestamp(timestamp, tz=timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def publish_heartbeat(source, snapshot, target, uid=0, gid=POD_GID):
    directory = target.parent

    if directory.is_symlink():
        raise RuntimeError("Unsafe heartbeat directory")

    directory_info = directory.stat()

    if (
        directory_info.st_uid != uid
        or directory_info.st_gid != gid
        or stat.S_IMODE(directory_info.st_mode) & 0o027
    ):
        raise RuntimeError("Unsafe heartbeat directory permissions")

    for path in (source, snapshot):
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("Unsafe or missing telemetry file")

    source_info = source.stat()
    snapshot_info = snapshot.stat()

    if (
        snapshot_info.st_uid != uid
        or snapshot_info.st_gid != gid
        or stat.S_IMODE(snapshot_info.st_mode) != 0o440
    ):
        raise RuntimeError("Unsafe snapshot permissions")

    if target.is_symlink():
        raise RuntimeError("Heartbeat cannot be a symlink")

    if target.exists():
        existing = target.stat()

        if (
            not stat.S_ISREG(existing.st_mode)
            or existing.st_uid != uid
            or existing.st_gid != gid
            or stat.S_IMODE(existing.st_mode) != 0o440
        ):
            raise RuntimeError("Unsafe existing heartbeat")

    now = datetime.now(timezone.utc).timestamp()

    payload = {
        "schema_version": 1,
        "component": "zeek_publisher",
        "result": "success",
        "last_success_at_utc": utc_time(now),
        "input_updated_at_utc": utc_time(source_info.st_mtime),
        "snapshot_updated_at_utc": utc_time(snapshot_info.st_mtime),
        "input_bytes": source_info.st_size,
        "snapshot_bytes": snapshot_info.st_size,
    }

    fd, temporary = tempfile.mkstemp(
        prefix=".publisher-health-",
        dir=directory,
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())

            if info.st_uid != uid or info.st_gid != gid:
                os.fchown(stream.fileno(), uid, gid)

            os.fchmod(stream.fileno(), 0o440)

            json.dump(payload, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(temporary, target)

        directory_fd = os.open(
            directory,
            os.O_RDONLY | os.O_DIRECTORY,
        )
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

    return payload


if __name__ == "__main__":
    result = publish_heartbeat(
        SOURCE,
        SNAPSHOT,
        HEARTBEAT,
    )

    print(
        "HEARTBEAT_OK",
        result["last_success_at_utc"],
    )
