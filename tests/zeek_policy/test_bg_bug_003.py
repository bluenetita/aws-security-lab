"""BG-BUG-003 adaptive host and destination recovery acceptance tests."""

import unittest

from _support import ZeekHarness, heartbeat_pcap, records, timed_capacity_script


class AdaptiveCapacityRecoveryAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = ZeekHarness()

    @classmethod
    def tearDownClass(cls):
        cls.harness.close()

    def test_host_identity_admitted_after_inactivity(self):
        data = self.harness.run_script(
            "bg_bug_003_host", timed_capacity_script("host"),
            pcap=heartbeat_pcap(), ignore_checksums=True,
        )
        rows = records(data, "adaptive", "host")
        self.assertEqual([(r["src_ip"], r["profile_state"]) for r in rows],
                         [("10.20.1.11", "training"),
                          ("10.20.1.12", "capacity_exceeded"),
                          ("10.20.1.12", "training")])
        self.assertEqual((rows[-1]["ts"], rows[-1]["profile_samples_before"],
                          rows[-1]["baseline_sample_queued"]),
                         (4801.0, 0, True))
        self.assertEqual(
            rows[-1]["profile_state"], "training",
            "BG-BUG-003: a new host must regain capacity after prolonged inactivity",
        )

    def test_destination_identity_admitted_after_inactivity(self):
        data = self.harness.run_script(
            "bg_bug_003_destination", timed_capacity_script("destination"),
            pcap=heartbeat_pcap(), ignore_checksums=True,
        )
        rows = records(data, "adaptive", "destination")
        self.assertEqual([(r["dest_ip"], r["profile_state"]) for r in rows],
                         [("198.51.100.1", "training"),
                          ("198.51.100.2", "capacity_exceeded"),
                          ("198.51.100.2", "training")])
        self.assertEqual((rows[-1]["ts"], rows[-1]["profile_samples_before"],
                          rows[-1]["baseline_sample_queued"]),
                         (4801.0, 0, True))
        self.assertEqual(
            rows[-1]["profile_state"], "training",
            "BG-BUG-003: a new destination must regain capacity after prolonged inactivity",
        )


if __name__ == "__main__":
    unittest.main()
