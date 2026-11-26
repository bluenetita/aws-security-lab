"""Bounded private-store ingestion using only temporary paths."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _support import CONTROL, connection, jsonl, load_script


ingester = load_script("host_ingester", CONTROL / "blueguard-ingest-jsonl")


class IngesterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name) / "private"
        self.base.mkdir(mode=0o700)
        self.store = self.base / "conn.jsonl"
        self.paths = mock.patch.multiple(
            ingester, BASE=self.base, STORE=self.store,
            LOCK=self.base / ".ingest.lock"
        )
        self.paths.start()
        self.addCleanup(self.paths.stop)

    def ingest(self, payload):
        output = io.StringIO()
        with mock.patch.object(ingester.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(payload))):
            with contextlib.redirect_stdout(output):
                ingester.main()
        return output.getvalue()

    def test_new_then_replayed_batch_is_deduplicated(self):
        payload = jsonl(connection())
        self.assertEqual(self.ingest(payload), "OK new=1 duplicates=0 total=1\n")
        self.assertEqual(self.ingest(payload), "OK new=0 duplicates=1 total=1\n")
        self.assertEqual(self.store.read_bytes(), payload)
        self.assertEqual(self.store.stat().st_mode & 0o777, 0o600)

    def test_duplicate_within_one_batch(self):
        record = connection()
        self.assertEqual(
            self.ingest(jsonl(record, record)),
            "OK new=1 duplicates=1 total=1\n",
        )
        self.assertEqual(len(self.store.read_bytes().splitlines()), 1)

    def test_malformed_record_rejects_whole_batch(self):
        original = jsonl(connection("C1"))
        self.ingest(original)
        with self.assertRaises(ValueError):
            self.ingest(jsonl(connection("C2")) + b"{bad json}\n")
        self.assertEqual(self.store.read_bytes(), original)

    def test_oversized_batch_and_record_leave_store_unchanged(self):
        original = jsonl(connection("C1"))
        self.ingest(original)
        with self.assertRaisesRegex(ValueError, "oversized batch"):
            self.ingest(b"x" * (ingester.MAX_BATCH + 1))
        with self.assertRaisesRegex(ValueError, "Oversized record"):
            self.ingest(b"{" + b"x" * 65536 + b"\n")
        self.assertEqual(self.store.read_bytes(), original)

    def test_byte_capacity_boundary(self):
        payload = jsonl(connection())
        with mock.patch.object(ingester, "MAX_STORE", len(payload)):
            self.ingest(payload)
        self.assertEqual(self.store.read_bytes(), payload)

        next_payload = jsonl(connection("C2"))
        with mock.patch.object(ingester, "MAX_STORE", len(payload) + len(next_payload) - 1):
            with self.assertRaisesRegex(ValueError, "Storage limit"):
                self.ingest(next_payload)
        self.assertEqual(self.store.read_bytes(), payload)

    def test_record_capacity_boundary(self):
        self.ingest(jsonl(connection("C1")))
        with mock.patch.object(ingester, "MAX_RECORDS", 1):
            with self.assertRaisesRegex(ValueError, "Record limit"):
                self.ingest(jsonl(connection("C2")))
        self.assertEqual(len(self.store.read_bytes().splitlines()), 1)

    def test_replace_failure_keeps_previous_generation(self):
        original = jsonl(connection("C1"))
        self.ingest(original)
        with mock.patch.object(ingester.os, "replace", side_effect=OSError("synthetic replace failure")):
            with self.assertRaisesRegex(OSError, "synthetic replace"):
                self.ingest(jsonl(connection("C2")))
        self.assertEqual(self.store.read_bytes(), original)
        self.assertEqual(list(self.base.glob(".conn-*")), [])

    def test_store_symlink_is_rejected(self):
        target = self.base / "other.jsonl"
        target.write_bytes(jsonl(connection("C1")))
        self.store.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "Invalid storage path"):
            self.ingest(jsonl(connection("C2")))
        self.assertEqual(target.read_bytes(), jsonl(connection("C1")))


if __name__ == "__main__":
    unittest.main()
