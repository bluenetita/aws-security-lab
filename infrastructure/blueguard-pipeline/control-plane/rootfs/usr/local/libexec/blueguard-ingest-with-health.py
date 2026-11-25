#!/usr/bin/env python3
"""Execute the existing ingester and record successful batches."""

import fcntl
import json
import os
import pwd
import re
import stat
import subprocess
import sys
import tempfile

from datetime import datetime, timezone
from pathlib import Path


BASE = Path("/var/lib/blueguard-ingest/incoming")
INGESTER = "/usr/local/libexec/blueguard-ingest-jsonl"


def utc_time(timestamp):
    return (
        datetime.fromtimestamp(timestamp, timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def write_receipt(response, base=BASE):
    match = re.fullmatch(
        rb"OK new=(\d+) duplicates=(\d+) total=(\d+)\n",
        response,
    )

    if match is None:
        raise ValueError("Unexpected ingester success response")

    new, duplicates, total = (
        int(value) for value in match.groups()
    )

    if new + duplicates < 1 or new > total or total > 10000:
        raise ValueError("Inconsistent ingestion counters")

    directory_info = base.lstat()

    if (
        not stat.S_ISDIR(directory_info.st_mode)
        or directory_info.st_uid != os.geteuid()
        or stat.S_IMODE(directory_info.st_mode) != 0o700
    ):
        raise RuntimeError("Unsafe ingestion directory")

    store = base / "conn.jsonl"
    store_info = store.lstat()

    if (
        not stat.S_ISREG(store_info.st_mode)
        or store_info.st_uid != os.geteuid()
        or stat.S_IMODE(store_info.st_mode) != 0o600
    ):
        raise RuntimeError("Unsafe ingestion store")

    receipt = base / "ingestion-health.json"

    try:
        previous = receipt.lstat()
    except FileNotFoundError:
        pass
    else:
        if (
            not stat.S_ISREG(previous.st_mode)
            or previous.st_uid != os.geteuid()
            or stat.S_IMODE(previous.st_mode) != 0o600
        ):
            raise RuntimeError("Unsafe existing receipt")

    payload = {
        "schema_version": 1,
        "component": "zeek_ingestion",
        "result": "success",
        "last_valid_batch_at_utc": utc_time(
            datetime.now(timezone.utc).timestamp()
        ),
        "store_updated_at_utc": utc_time(
            store_info.st_mtime
        ),
        "last_batch_new_records": new,
        "last_batch_duplicate_records": duplicates,
        "total_records_after_batch": total,
    }

    fd, temporary = tempfile.mkstemp(
        prefix=".ingestion-health-",
        dir=base,
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(payload, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(temporary, receipt)

        directory_fd = os.open(
            base,
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


def main():
    account = pwd.getpwnam("blueguard-ingest")

    if os.geteuid() != account.pw_uid:
        raise RuntimeError("Wrong execution account")

    lock_path = BASE / ".receiver-health.lock"

    if lock_path.is_symlink():
        raise RuntimeError("Invalid receiver lock")

    with lock_path.open("a+b") as lock:
        lock_info = os.fstat(lock.fileno())

        if (
            not stat.S_ISREG(lock_info.st_mode)
            or lock_info.st_uid != os.geteuid()
            or stat.S_IMODE(lock_info.st_mode) != 0o600
        ):
            raise RuntimeError("Unsafe receiver lock")

        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)

        result = subprocess.run(
            ["/usr/bin/python3", "-B", INGESTER],
            stdin=sys.stdin.buffer,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=45,
            check=False,
        )

        if result.returncode != 0:
            sys.stderr.buffer.write(result.stderr)
            return 1

        write_receipt(result.stdout)

        sys.stdout.buffer.write(result.stdout)
        return 0


if __name__ == "__main__":
    os.umask(0o077)

    try:
        sys.exit(main())
    except (
        OSError,
        ValueError,
        RuntimeError,
        subprocess.TimeoutExpired,
    ) as exc:
        print(
            f"INGEST_RECEIPT_ERROR: {type(exc).__name__}",
            file=sys.stderr,
        )
        sys.exit(1)
