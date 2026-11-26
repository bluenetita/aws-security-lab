"""Collector checkpoint and rotation tests; transport is always mocked."""

import contextlib
import gzip
import hashlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _support import SENSOR, connection, jsonl, load_script


collector_module = load_script("host_collector", SENSOR / "blueguard-zeek-collector")


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "logs"
        self.state = Path(self.temp.name) / "state"
        (self.root / "current").mkdir(parents=True)
        self.sent = []

        def sender(payload, count):
            self.sent.append((payload, count))

        self.sender = sender

    def new_collector(self, sender=None):
        return collector_module.Collector(
            self.root, self.state, "2026-11-19", sender or self.sender
        )

    def assert_active(self, offset, processed):
        active = self.new_collector().state["active"]
        sample = processed[max(0, offset - collector_module.CONTINUITY_BYTES):offset]
        self.assertEqual(active["offset"], offset)
        self.assertEqual(active["continuity"], {
            "offset": offset,
            "window_bytes": len(sample),
            "sha256": hashlib.sha256(sample).hexdigest(),
        })
        return active

    def test_incremental_current_waits_for_complete_line(self):
        path = self.root / "current/conn.log"
        first = jsonl(connection("C1"))
        second = jsonl(connection("C2"))
        path.write_bytes(first + second[:-1])

        self.new_collector().run()
        self.assertEqual(self.sent, [(first, 1)])
        self.assert_active(len(first), first)

        path.write_bytes(first + second)
        self.new_collector().run()
        self.assertEqual(self.sent[-1], (second, 1))
        self.new_collector().run()
        self.assertEqual(len(self.sent), 2)
        self.assert_active(len(first + second), first + second)

    def test_rotation_processes_archive_and_new_inode(self):
        current = self.root / "current/conn.log"
        first = jsonl(connection("C1"))
        second = jsonl(connection("C2"))
        current.write_bytes(first)
        self.new_collector().run()
        old_inode = self.new_collector().state["active"]["ino"]

        archive_dir = self.root / "2026-11-19"
        archive_dir.mkdir()
        with gzip.open(archive_dir / "conn.1.log.gz", "wb") as stream:
            stream.write(first)
        # Keep the old inode allocated, as a rename-based rotation does.
        current.rename(self.root / "rotated-conn.log")
        current.write_bytes(second)

        self.new_collector().run()
        state = self.new_collector().state
        self.assertNotEqual(state["active"]["ino"], old_inode)
        self.assert_active(len(second), second)
        self.assertTrue(state["archives"][str(archive_dir / "conn.1.log.gz")]["complete"])
        self.assertEqual(self.sent[-2:], [(first, 1), (second, 1)])
        self.new_collector().run()
        self.assertEqual(len(self.sent), 3)

    def test_copytruncate_refill_to_same_size_replays(self):
        current = self.root / "current/conn.log"
        first = jsonl(connection("C1"))
        second = jsonl(connection("C2"))
        self.assertEqual(len(first), len(second))
        current.write_bytes(first)
        self.new_collector().run()
        self.assert_active(len(first), first)
        current.write_bytes(second)  # Same inode and final size.
        with contextlib.redirect_stderr(io.StringIO()) as warning:
            self.new_collector().run()
        self.assertIn("continuity changed", warning.getvalue())
        self.assertEqual(self.sent, [(first, 1), (second, 1)])
        self.assert_active(len(second), second)

    def test_copytruncate_refill_to_larger_size_replays_all_records(self):
        current = self.root / "current/conn.log"
        first = jsonl(connection("C1"))
        second = jsonl(connection("C2"))
        third = jsonl(connection("C3"))
        current.write_bytes(first)
        self.new_collector().run()
        current.write_bytes(second + third)
        with contextlib.redirect_stderr(io.StringIO()) as warning:
            self.new_collector().run()
        self.assertIn("continuity changed", warning.getvalue())
        self.assertEqual(self.sent, [(first, 1), (second + third, 2)])
        self.assert_active(len(second + third), second + third)

    def test_smaller_truncation_resets_offset(self):
        current = self.root / "current/conn.log"
        first = jsonl(connection("C1"))
        current.write_bytes(first + jsonl(connection("C2")))
        self.new_collector().run()
        current.write_bytes(first)
        with contextlib.redirect_stderr(io.StringIO()) as warning:
            self.new_collector().run()
        self.assertIn("shrank", warning.getvalue())
        self.assertEqual(self.sent[-1], (first, 1))
        self.assert_active(len(first), first)

    def test_legacy_offset_replays_and_preserves_archive_state(self):
        current = self.root / "current/conn.log"
        payload = jsonl(connection("C1"), connection("C2"))
        current.write_bytes(payload)
        info = current.stat()
        archives = {"old": {"fingerprint": [1, 2], "lines": 3, "complete": True}}
        self.state.mkdir()
        (self.state / "state.json").write_text(json.dumps({
            "version": 1, "archives": archives,
            "active": {"dev": info.st_dev, "ino": info.st_ino,
                       "offset": len(jsonl(connection("C1")))},
        }))
        with contextlib.redirect_stderr(io.StringIO()) as warning:
            self.new_collector().process_current()
        self.assertIn("Legacy active checkpoint", warning.getvalue())
        self.assertEqual(self.sent, [(payload, 2)])
        self.assert_active(len(payload), payload)
        self.assertEqual(self.new_collector().state["archives"], archives)

    def test_malformed_continuity_is_rejected_without_replay(self):
        current = self.root / "current/conn.log"
        current.write_bytes(jsonl(connection()))
        info = current.stat()
        self.state.mkdir()
        state_file = self.state / "state.json"
        for continuity in (
            {"offset": 1, "window_bytes": 1, "sha256": "0" * 64},
            {"offset": len(current.read_bytes()), "window_bytes": 1,
             "sha256": "0" * 64},
            {"offset": len(current.read_bytes()), "window_bytes": len(current.read_bytes()),
             "sha256": "not-a-digest"},
        ):
            with self.subTest(continuity=continuity):
                state_file.write_text(json.dumps({
                    "version": 1, "archives": {},
                    "active": {"dev": info.st_dev, "ino": info.st_ino,
                               "offset": len(current.read_bytes()),
                               "continuity": continuity},
                }))
                with self.assertRaisesRegex(ValueError, "continuity checkpoint"):
                    self.new_collector()
                self.assertEqual(self.sent, [])

    def test_failed_delivery_retries_without_checkpoint(self):
        payload = jsonl(connection())
        (self.root / "current/conn.log").write_bytes(payload)
        attempts = []

        def failing_sender(data, count):
            attempts.append(data)
            raise RuntimeError("synthetic transport failure")

        with self.assertRaisesRegex(RuntimeError, "synthetic transport"):
            self.new_collector(failing_sender).run()
        self.assertFalse((self.state / "state.json").exists())

        self.new_collector().run()
        self.assertEqual(attempts, [payload])
        self.assertEqual(self.sent, [(payload, 1)])
        self.assert_active(len(payload), payload)

    def test_second_batch_ack_failure_keeps_first_batch_checkpoint(self):
        current = self.root / "current/conn.log"
        first_batch = b"".join(jsonl(connection(f"C{i:03}")) for i in range(100))
        separator = b"\n"
        last = jsonl(connection("C100"))
        current.write_bytes(first_batch + separator + last)
        replies = [
            subprocess.CompletedProcess([], 0, b"OK new=100 duplicates=0 total=100\n", b""),
            subprocess.CompletedProcess([], 0, b"OK new=0 duplicates=0 total=100\n", b""),
        ]
        with mock.patch.object(collector_module.subprocess, "run", side_effect=replies) as run:
            with self.assertRaisesRegex(RuntimeError, "wrong number"):
                self.new_collector(collector_module.send_batch).run()
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].kwargs["input"], first_batch)
        self.assertEqual(run.call_args_list[1].kwargs["input"], last)
        self.assert_active(len(first_batch + separator), first_batch + separator)
        self.new_collector().run()
        self.assertEqual(self.sent, [(last, 1)])
        self.assert_active(len(first_batch + separator + last), first_batch + separator + last)

    def test_ack_before_checkpoint_failure_replays_on_retry(self):
        payload = jsonl(connection())
        (self.root / "current/conn.log").write_bytes(payload)
        with mock.patch.object(collector_module, "atomic_json", side_effect=FileNotFoundError("state path failed")):
            with self.assertRaisesRegex(FileNotFoundError, "state path failed"):
                self.new_collector().run()
        self.assertEqual(self.sent, [(payload, 1)])
        self.assertFalse((self.state / "state.json").exists())
        self.new_collector().run()
        self.assertEqual(self.sent, [(payload, 1), (payload, 1)])
        self.assert_active(len(payload), payload)

    def test_concurrent_rewrite_before_delivery_is_rejected(self):
        current = self.root / "current/conn.log"
        first = jsonl(connection("C1"))
        second = jsonl(connection("C2"))
        current.write_bytes(first)
        original = collector_module.Collector.safe_line

        def rewrite_after_read(line, name):
            result = original(line, name)
            current.write_bytes(second)
            return result

        with mock.patch.object(collector_module.Collector, "safe_line", side_effect=rewrite_after_read):
            with self.assertRaisesRegex(RuntimeError, "changed during collection"):
                self.new_collector().run()
        self.assertEqual(self.sent, [])
        self.assertFalse((self.state / "state.json").exists())

    def test_continuity_read_ignores_buffered_read_ahead(self):
        current = self.root / "current/conn.log"
        current.write_bytes(b"a" * 8192)
        with current.open("rb") as stream:
            self.assertEqual(stream.read(1), b"a")  # Populate Python's read buffer.
            with current.open("r+b", buffering=0) as writer:
                writer.seek(100)
                writer.write(b"z")
                os.fsync(writer.fileno())
            self.assertEqual(collector_module.read_window(stream, 101, 1), b"z")
            self.assertEqual(stream.tell(), 1)

    def test_rewrite_during_first_ack_aborts_then_replays_replacement(self):
        current = self.root / "current/conn.log"
        original = [jsonl(connection(f"C{i:03}")) for i in range(201)]
        replacement = [jsonl(connection(f"R{i:03}")) for i in range(100)]
        self.assertEqual(len(b"".join(original[:100])), len(b"".join(replacement)))
        self.assertGreater(len(b"".join(original[:100])), collector_module.CONTINUITY_BYTES)
        current.write_bytes(b"".join(original))
        attempted = []

        def rewrite_during_ack(payload, count):
            attempted.append((payload, count))
            current.write_bytes(b"".join(replacement + original[100:]))

        with self.assertRaisesRegex(RuntimeError, "continuity") as failure:
            self.new_collector(rewrite_during_ack).run()
        self.assertNotIn("C000", str(failure.exception))
        self.assertEqual(attempted, [(b"".join(original[:100]), 100)])
        self.assertFalse((self.state / "state.json").exists())

        self.new_collector().run()
        self.assertEqual([count for _, count in self.sent], [100, 100, 1])
        self.assertEqual(b"".join(payload for payload, _ in self.sent),
                         b"".join(replacement + original[100:]))
        self.assert_active(current.stat().st_size, current.read_bytes())

    def test_rewrite_after_previous_checkpoint_preserves_progress(self):
        current = self.root / "current/conn.log"
        first = [jsonl(connection(f"C{i:03}")) for i in range(100)]
        later = [jsonl(connection(f"C{i:03}")) for i in range(100, 201)]
        current.write_bytes(b"".join(first))
        self.new_collector().run()
        committed = len(b"".join(first))
        original_active = self.assert_active(committed, current.read_bytes())
        current.write_bytes(b"".join(first + later))
        replacement = jsonl(connection("R099"))
        self.assertEqual(len(first[-1]), len(replacement))
        attempted = []

        def rewrite_prior_anchor(payload, count):
            attempted.append((payload, count))
            current.write_bytes(b"".join(first[:-1] + [replacement] + later))

        with self.assertRaisesRegex(RuntimeError, "continuity"):
            self.new_collector(rewrite_prior_anchor).run()
        self.assertEqual(attempted, [(b"".join(later[:100]), 100)])
        self.assertEqual(self.new_collector().state["active"], original_active)

    def test_lookahead_rewrite_during_ack_stops_next_batch(self):
        current = self.root / "current/conn.log"
        first = b"".join(jsonl(connection(f"C{i:03}")) for i in range(100))
        lookahead = jsonl(connection("C100"))
        replacement = jsonl(connection("R100"))
        self.assertEqual(len(lookahead), len(replacement))
        current.write_bytes(first + lookahead)
        attempted = []

        def rewrite_lookahead(payload, count):
            attempted.append((payload, count))
            current.write_bytes(first + replacement)

        with self.assertRaisesRegex(RuntimeError, "continuity"):
            self.new_collector(rewrite_lookahead).run()
        self.assertEqual(attempted, [(first, 100)])
        self.assert_active(len(first), first)
        self.new_collector().run()
        self.assertEqual(self.sent, [(replacement, 1)])
        self.assert_active(len(first + replacement), first + replacement)

    def test_append_during_ack_is_not_a_discontinuity(self):
        current = self.root / "current/conn.log"
        first = b"".join(jsonl(connection(f"C{i:03}")) for i in range(100))
        appended = jsonl(connection("C100"))
        current.write_bytes(first)

        def append_during_ack(payload, count):
            self.sent.append((payload, count))
            with current.open("ab") as stream:
                stream.write(appended)

        self.new_collector(append_during_ack).run()
        self.assertEqual(self.sent, [(first, 100)])
        self.assert_active(len(first), first)
        self.new_collector().run()
        self.assertEqual(self.sent[-1], (appended, 1))
        self.assert_active(len(first + appended), first + appended)

    def test_missing_active_log_is_benign(self):
        self.new_collector().run()
        self.assertEqual(self.sent, [])
        self.assertFalse((self.state / "state.json").exists())

    def test_transport_file_not_found_is_not_masked(self):
        (self.root / "current/conn.log").write_bytes(jsonl(connection()))

        def missing_transport(payload, count):
            raise FileNotFoundError("synthetic transport missing")

        with self.assertRaisesRegex(FileNotFoundError, "synthetic transport missing"):
            self.new_collector(missing_transport).run()
        self.assertFalse((self.state / "state.json").exists())

    def test_checkpoint_file_not_found_is_not_masked(self):
        (self.root / "current/conn.log").write_bytes(jsonl(connection()))
        with mock.patch.object(collector_module.Collector, "save", side_effect=FileNotFoundError("synthetic state missing")):
            with self.assertRaisesRegex(FileNotFoundError, "synthetic state missing"):
                self.new_collector().run()
        self.assertFalse((self.state / "state.json").exists())

    def test_invalid_ack_does_not_count_as_delivery(self):
        result = subprocess.CompletedProcess([], 0, b"OK new=0 duplicates=0 total=0\n", b"")
        with mock.patch.object(collector_module.subprocess, "run", return_value=result) as run:
            with self.assertRaisesRegex(RuntimeError, "wrong number"):
                collector_module.send_batch(jsonl(connection()), 1)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.kwargs["input"], jsonl(connection()))

    def test_malformed_and_oversized_lines_do_not_advance(self):
        path = self.root / "current/conn.log"
        for data in (b"{bad json}\n", b"{" + b"x" * 65536 + b"\n"):
            with self.subTest(size=len(data)):
                path.write_bytes(data)
                with self.assertRaises((ValueError, UnicodeError)):
                    self.new_collector().run()
                self.assertFalse((self.state / "state.json").exists())
        self.assertEqual(self.sent, [])


if __name__ == "__main__":
    unittest.main()
