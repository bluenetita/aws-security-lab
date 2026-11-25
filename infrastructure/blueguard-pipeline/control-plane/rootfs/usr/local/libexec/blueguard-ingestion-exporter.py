#!/usr/bin/env python3
"""Validate and publish BlueGuard ingestion health receipts."""

import json
import os
import pwd
import stat
import sys
import tempfile

from datetime import datetime, timedelta, timezone
from pathlib import Path


SOURCE = Path("/var/lib/blueguard-ingest/incoming")
DESTINATION = Path("/var/lib/blueguard/zeek")

SOURCE_NAME = "ingestion-health.json"
DESTINATION_NAME = "ingestion-health.json"

PUBLISH_GID = 10001
MAX_BYTES = 4096
MAX_RECORDS = 10000

DIRECTORY_FLAGS = (
    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
)
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW


def checked_directory(path, uid, gid, mode):
    fd = os.open(path, DIRECTORY_FLAGS)

    try:
        info = os.fstat(fd)

        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != uid
            or info.st_gid != gid
            or stat.S_IMODE(info.st_mode) != mode
        ):
            raise ValueError("Unsafe directory permissions")

        return fd

    except BaseException:
        os.close(fd)
        raise


def checked_file(directory_fd, name, uid, gid, mode):
    fd = os.open(name, FILE_FLAGS, dir_fd=directory_fd)

    try:
        info = os.fstat(fd)

        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != uid
            or info.st_gid != gid
            or stat.S_IMODE(info.st_mode) != mode
            or info.st_nlink != 1
        ):
            raise ValueError("Unsafe receipt file")

        if not 0 < info.st_size <= MAX_BYTES:
            raise ValueError("Invalid receipt size")

        chunks = []
        remaining = MAX_BYTES + 1

        while remaining:
            chunk = os.read(fd, remaining)

            if not chunk:
                break

            chunks.append(chunk)
            remaining -= len(chunk)

        data = b"".join(chunks)

        if not 0 < len(data) <= MAX_BYTES:
            raise ValueError("Invalid receipt contents")

        return data

    finally:
        os.close(fd)


def parse_timestamp(value):
    if (
        not isinstance(value, str)
        or not value.endswith("Z")
        or len(value) > 40
    ):
        raise ValueError("Invalid UTC timestamp")

    try:
        parsed = datetime.fromisoformat(
            value[:-1] + "+00:00"
        )
    except ValueError as exc:
        raise ValueError("Invalid timestamp format") from exc

    if parsed.utcoffset() != timedelta(0):
        raise ValueError("Timestamp must be UTC")

    if parsed > datetime.now(timezone.utc) + timedelta(seconds=60):
        raise ValueError("Timestamp is in the future")

    return parsed


def validate_receipt(raw):
    data = json.loads(raw)

    if not isinstance(data, dict):
        raise ValueError("Receipt must be an object")

    if (
        type(data.get("schema_version")) is not int
        or data["schema_version"] != 1
        or data.get("component") != "zeek_ingestion"
        or data.get("result") != "success"
    ):
        raise ValueError("Invalid receipt schema")

    last_batch = parse_timestamp(
        data.get("last_valid_batch_at_utc")
    )

    store_updated = parse_timestamp(
        data.get("store_updated_at_utc")
    )

    if store_updated > last_batch + timedelta(seconds=60):
        raise ValueError("Inconsistent timestamps")

    fields = (
        "last_batch_new_records",
        "last_batch_duplicate_records",
        "total_records_after_batch",
    )

    for field in fields:
        value = data.get(field)

        if type(value) is not int or not 0 <= value <= MAX_RECORDS:
            raise ValueError(f"Invalid counter: {field}")

    new = data["last_batch_new_records"]
    duplicates = data["last_batch_duplicate_records"]
    total = data["total_records_after_batch"]

    if new + duplicates < 1 or new > total:
        raise ValueError("Inconsistent ingestion counters")

    # Reconstruct a canonical document with approved fields only.
    return {
        "schema_version": 1,
        "component": "zeek_ingestion",
        "result": "success",
        "last_valid_batch_at_utc":
            data["last_valid_batch_at_utc"],
        "store_updated_at_utc":
            data["store_updated_at_utc"],
        "last_batch_new_records": new,
        "last_batch_duplicate_records": duplicates,
        "total_records_after_batch": total,
    }


def publish(source=SOURCE, destination=DESTINATION):
    account = pwd.getpwnam("blueguard-ingest")

    if os.geteuid() != 0:
        raise RuntimeError("Exporter must run as root")

    source_fd = checked_directory(
        source, account.pw_uid, account.pw_gid, 0o700
    )

    try:
        raw = checked_file(
            source_fd,
            SOURCE_NAME,
            account.pw_uid,
            account.pw_gid,
            0o600,
        )
    finally:
        os.close(source_fd)

    data = validate_receipt(raw)

    payload = (
        json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode("utf-8")

    destination_fd = checked_directory(
        destination, 0, PUBLISH_GID, 0o750
    )

    try:
        try:
            existing = checked_file(
                destination_fd,
                DESTINATION_NAME,
                0,
                PUBLISH_GID,
                0o440,
            )
        except FileNotFoundError:
            existing = None

        if existing == payload:
            print("UNCHANGED: ingestion receipt already published")
            return data

        fd, temporary = tempfile.mkstemp(
            prefix=".ingestion-health-",
            dir=destination,
        )

        try:
            with os.fdopen(fd, "wb") as stream:
                os.fchown(stream.fileno(), 0, PUBLISH_GID)
                os.fchmod(stream.fileno(), 0o440)

                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())

            os.replace(
                temporary,
                destination / DESTINATION_NAME,
            )

            os.fsync(destination_fd)

        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    finally:
        os.close(destination_fd)

    print(
        "PUBLISHED: last valid batch "
        + data["last_valid_batch_at_utc"]
    )

    return data


if __name__ == "__main__":
    try:
        publish()
    except (
        OSError,
        ValueError,
        RuntimeError,
        KeyError,
        TypeError,
    ) as exc:
        print(
            f"INGESTION_EXPORT_FAILED: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
