"""Automated tests for the Zeek snapshot loader."""

import json
import tempfile
import unittest

from pathlib import Path

from app.zeek import load_zeek_snapshot


class TestZeekSnapshot(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.file = Path(self.temp_dir.name) / "conn.jsonl"

        self.event = {
            "ts": 1795098475.313673,
            "uid": "CQN9op1cWFef1nHdCj",
            "id.orig_h": "10.20.1.11",
            "id.orig_p": 34588,
            "id.resp_h": "10.20.1.10",
            "id.resp_p": 18080,
            "proto": "tcp",
            "service": "http",
            "duration": 160.079,
            "orig_bytes": 5243137,
            "resp_bytes": 369,
            "conn_state": "SF",
            "missed_bytes": 0
        }

    def write_events(self, *events):
        with self.file.open("w", encoding="utf-8") as stream:
            for event in events:
                stream.write(json.dumps(event) + "\n")

    def test_valid_connection(self):
        self.write_events(self.event)

        result = load_zeek_snapshot(self.file)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].uid, self.event["uid"])
        self.assertEqual(result[0].missed_bytes, 0)
        self.assertEqual(result[0].provenance, "zeek_snapshot")

    def test_invalid_source_ip(self):
        event = dict(self.event)
        event["id.orig_h"] = "not-an-ip"

        self.write_events(event)

        with self.assertRaises(ValueError):
            load_zeek_snapshot(self.file)

    def test_invalid_port(self):
        event = dict(self.event)
        event["id.orig_p"] = 70000

        self.write_events(event)

        with self.assertRaises(ValueError):
            load_zeek_snapshot(self.file)

    def test_duplicate_connections(self):
        self.write_events(self.event, self.event)

        with self.assertRaises(ValueError):
            load_zeek_snapshot(self.file)

    def test_invalid_json(self):
        self.file.write_text(
            "{invalid json}\n",
            encoding="utf-8"
        )

        with self.assertRaises(ValueError):
            load_zeek_snapshot(self.file)

    def test_missing_missed_bytes(self):
        event = dict(self.event)
        event.pop("missed_bytes")

        self.write_events(event)

        result = load_zeek_snapshot(self.file)

        self.assertIsNone(result[0].missed_bytes)

    def test_empty_snapshot(self):
        self.file.write_text("", encoding="utf-8")

        with self.assertRaises(ValueError):
            load_zeek_snapshot(self.file)


if __name__ == "__main__":
    unittest.main()
