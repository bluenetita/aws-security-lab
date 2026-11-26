"""Publisher and health boundary tests with synthetic temporary files."""

import json
import os
import stat
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _support import CONTROL, connection, jsonl, load_script


publisher = load_script("host_publisher", CONTROL / "blueguard-zeek-publisher")
heartbeat = load_script("host_heartbeat", CONTROL / "blueguard-zeek-heartbeat.py")
receipt_writer = load_script("host_receipt_writer", CONTROL / "blueguard-ingest-with-health.py")
exporter = load_script("host_exporter", CONTROL / "blueguard-ingestion-exporter.py")


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.private = Path(self.temp.name) / "private"
        self.public = Path(self.temp.name) / "published"
        self.private.mkdir(mode=0o700)
        self.public.mkdir(mode=0o700)
        self.source = self.private / "conn.jsonl"
        self.snapshot = self.public / "conn-ingested.jsonl"

    def publish(self):
        # The production destination must be root:10001. Only metadata and
        # ownership operations are mocked; content and replace use temp files.
        original_stat = Path.stat
        directory = self.public

        def synthetic_directory_stat(path, *args, **kwargs):
            if path == directory:
                return SimpleNamespace(st_uid=0, st_gid=publisher.POD_GID, st_mode=0o750)
            return original_stat(path, *args, **kwargs)

        with mock.patch.object(publisher, "SOURCE", self.source), mock.patch.object(
            publisher, "DEST", self.snapshot
        ), mock.patch.object(Path, "stat", synthetic_directory_stat), mock.patch.object(
            publisher.os, "fchown"
        ):
            publisher.main()

    def test_atomic_snapshot_publication_and_read_only_mode(self):
        payload = jsonl(connection())
        self.source.write_bytes(payload)
        self.publish()
        self.assertEqual(self.snapshot.read_bytes(), payload)
        self.assertEqual(stat.S_IMODE(self.snapshot.stat().st_mode), 0o440)
        self.publish()
        self.assertEqual(self.snapshot.read_bytes(), payload)

    def test_bad_source_does_not_replace_snapshot(self):
        original = jsonl(connection("C1"))
        self.source.write_bytes(original)
        self.publish()
        self.source.write_bytes(jsonl(connection("C2")) + b"{bad json}\n")
        with self.assertRaises(ValueError):
            self.publish()
        self.assertEqual(self.snapshot.read_bytes(), original)

    def test_replace_failure_preserves_published_snapshot(self):
        original = jsonl(connection("C1"))
        self.source.write_bytes(original)
        self.publish()
        self.source.write_bytes(jsonl(connection("C2")))
        with mock.patch.object(publisher.os, "replace", side_effect=OSError("synthetic replace failure")):
            with self.assertRaisesRegex(OSError, "synthetic replace"):
                self.publish()
        self.assertEqual(self.snapshot.read_bytes(), original)
        self.assertEqual(list(self.public.glob(".conn-ingested-*")), [])

    def test_oversized_source_does_not_replace_snapshot(self):
        original = jsonl(connection("C1"))
        self.source.write_bytes(original)
        self.publish()
        self.source.write_bytes(jsonl(connection("C2")))
        with mock.patch.object(publisher, "MAX_BYTES", self.source.stat().st_size - 1):
            with self.assertRaisesRegex(ValueError, "exceeds 10 MiB"):
                self.publish()
        self.assertEqual(self.snapshot.read_bytes(), original)

    def test_heartbeat_requires_snapshot_and_publishes_read_only(self):
        self.source.write_bytes(jsonl(connection()))
        with self.assertRaisesRegex(RuntimeError, "Unsafe or missing"):
            heartbeat.publish_heartbeat(
                self.source, self.snapshot, self.public / "publisher-health.json",
                uid=os.geteuid(), gid=os.getegid(),
            )
        self.snapshot.write_bytes(self.source.read_bytes())
        self.snapshot.chmod(0o440)
        target = self.public / "publisher-health.json"
        result = heartbeat.publish_heartbeat(
            self.source, self.snapshot, target,
            uid=os.geteuid(), gid=os.getegid(),
        )
        self.assertEqual(result["result"], "success")
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o440)
        self.assertEqual(json.loads(target.read_text())["snapshot_bytes"], self.snapshot.stat().st_size)

    def test_receipt_written_only_for_valid_ack_and_private_store(self):
        self.source.write_bytes(jsonl(connection()))
        self.source.chmod(0o600)
        with self.assertRaises(ValueError):
            receipt_writer.write_receipt(b"OK new=2 duplicates=0 total=1\n", base=self.private)
        self.assertFalse((self.private / "ingestion-health.json").exists())
        result = receipt_writer.write_receipt(b"OK new=1 duplicates=0 total=1\n", base=self.private)
        receipt = self.private / "ingestion-health.json"
        self.assertEqual(result["total_records_after_batch"], 1)
        self.assertEqual(stat.S_IMODE(receipt.stat().st_mode), 0o600)
        self.assertEqual(exporter.validate_receipt(receipt.read_bytes())["result"], "success")

    def test_receipt_writer_rejects_unsafe_store_permissions(self):
        self.source.write_bytes(jsonl(connection()))
        self.source.chmod(0o644)
        with self.assertRaisesRegex(RuntimeError, "Unsafe ingestion store"):
            receipt_writer.write_receipt(b"OK new=1 duplicates=0 total=1\n", base=self.private)

    def test_exporter_rejects_missing_malformed_and_future_health_data(self):
        valid = {
            "schema_version": 1,
            "component": "zeek_ingestion",
            "result": "success",
            "last_valid_batch_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "store_updated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "last_batch_new_records": 1,
            "last_batch_duplicate_records": 0,
            "total_records_after_batch": 1,
        }
        self.assertEqual(exporter.validate_receipt(json.dumps(valid).encode())["schema_version"], 1)
        for damaged in (b"{bad", b"{}", json.dumps({**valid, "total_records_after_batch": -1}).encode()):
            with self.subTest(damaged=damaged[:20]), self.assertRaises(ValueError):
                exporter.validate_receipt(damaged)
        future = (datetime.now(timezone.utc) + timedelta(minutes=3)).isoformat().replace("+00:00", "Z")
        with self.assertRaisesRegex(ValueError, "future"):
            exporter.validate_receipt(json.dumps({**valid, "last_valid_batch_at_utc": future}).encode())

    def test_exporter_enforces_private_directory_and_file_modes(self):
        self.source.write_bytes(b"{}\n")
        self.source.chmod(0o600)
        fd = exporter.checked_directory(self.private, os.geteuid(), os.getegid(), 0o700)
        try:
            with self.assertRaises(FileNotFoundError):
                exporter.checked_file(fd, "missing.json", os.geteuid(), os.getegid(), 0o600)
            self.assertEqual(
                exporter.checked_file(fd, self.source.name, os.geteuid(), os.getegid(), 0o600),
                b"{}\n",
            )
            (self.private / "linked.json").symlink_to(self.source)
            with self.assertRaises(OSError):
                exporter.checked_file(fd, "linked.json", os.geteuid(), os.getegid(), 0o600)
            self.source.chmod(0o644)
            with self.assertRaisesRegex(ValueError, "Unsafe receipt file"):
                exporter.checked_file(fd, self.source.name, os.geteuid(), os.getegid(), 0o600)
        finally:
            os.close(fd)
        self.private.chmod(0o755)
        with self.assertRaisesRegex(ValueError, "Unsafe directory"):
            exporter.checked_directory(self.private, os.geteuid(), os.getegid(), 0o700)


if __name__ == "__main__":
    unittest.main()
