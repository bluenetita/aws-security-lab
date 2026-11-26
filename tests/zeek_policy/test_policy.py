"""Persistent offline regressions for the recovered Zeek 9.0.1 policy."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from _support import (
    EVENT_HELPERS, ZeekHarness, destination, heartbeat_pcap, host, records,
    synthetic_tcp_pcap, timed_capacity_script,
)


HARNESS: ZeekHarness | None = None


def setUpModule() -> None:
    global HARNESS
    HARNESS = ZeekHarness()
    print(f"BlueGuard policy runtime: Zeek {HARNESS.version}, non-root")


def tearDownModule() -> None:
    assert HARNESS is not None
    HARNESS.close()
    print(f"BlueGuard policy assertions: {CountedCase.assertion_count}")


class CountedCase(unittest.TestCase):
    assertion_count = 0

    def assertEqual(self, first, second, msg=None):  # noqa: N802 - unittest API
        CountedCase.assertion_count += 1
        return super().assertEqual(first, second, msg)

    def events(self, name: str, lines: list[str], *, overrides: str = ""):
        assert HARNESS is not None
        return HARNESS.run_events(name, lines, overrides=overrides)


CONNECTION_EVENTS = [
    'emit_conn("BELOW",10.20.1.11,198.51.100.2,1023,"SF",T,0,F);',
    'emit_conn("AT",10.20.1.11,198.51.100.2,1024,"SF",T,0,F);',
    'emit_conn("UNPROTECTED",10.20.1.12,198.51.100.2,4096,"SF",T,0,F);',
    'emit_conn("EXTERNAL",198.51.100.2,10.20.1.11,2048,"SF",T,0,T);',
    'emit_conn("MISSING",10.20.1.11,198.51.100.2,0,"SF",F,0,F);',
    'emit_conn("PARTIAL",10.20.1.11,198.51.100.2,2048,"S1",T,0,F);',
    'emit_conn("GAP",10.20.1.11,198.51.100.2,2048,"SF",T,7,F);',
    'emit_conn("INTERNAL",10.20.1.11,10.20.1.11,4096,"SF",T,0,F);',
]


class TestLoadAndConnection(CountedCase):
    def connection_logs(self):
        return self.events("connection_events", CONNECTION_EVENTS)

    def test_policy_parses_with_bundled_dependencies(self):
        assert HARNESS is not None
        self.assertEqual(HARNESS.parse_policy(), None)

    def test_flow_threshold_and_protected_host_filter(self):
        flow = records(self.connection_logs(), "flow")
        self.assertEqual(sorted(row["uid"] for row in flow),
                         ["AT", "EXTERNAL", "GAP", "PARTIAL"])

    def test_external_initiation_orientation(self):
        flow = records(self.connection_logs(), "flow")
        self.assertEqual(next(row["flow_orientation"] for row in flow
                              if row["uid"] == "EXTERNAL"), "external_initiated")

    def test_capture_gap_flow_quality(self):
        flow = records(self.connection_logs(), "flow")
        self.assertEqual(next(row["data_quality"] for row in flow
                              if row["uid"] == "GAP"), "capture_gaps")

    def test_non_sf_flow_quality(self):
        flow = records(self.connection_logs(), "flow")
        self.assertEqual(next(row["data_quality"] for row in flow
                              if row["uid"] == "PARTIAL"), "partial_connection")

    def test_first_window_excluded(self):
        window = records(self.connection_logs(), "host_window")[0]
        self.assertEqual((window["first_window_partial"],
                          window["baseline_sample_eligible"]), (True, False))

    def test_missing_gap_and_non_sf_counters(self):
        window = records(self.connection_logs(), "host_window")[0]
        self.assertEqual((window["missing_outbound_byte_estimates"],
                          window["capture_gap_flows"], window["non_sf_flows"]),
                         (1, 1, 1))


class TestAdaptive(CountedCase):
    def test_cold_start_below_four_mib(self):
        data = self.events("cold_below", [host(1, 4194303)])
        self.assertEqual([r["adaptive_candidate"] for r in records(
            data, "adaptive", "host")], [False])

    def test_cold_start_at_four_mib(self):
        data = self.events("cold_at", [host(1, 4194304)])
        self.assertEqual([r["adaptive_candidate"] for r in records(
            data, "adaptive", "host")], [True])

    def training_logs(self):
        return self.events("training", [host(i, 100000) for i in range(1, 81)])

    def test_first_sample_queued_without_early_commit(self):
        first = records(self.training_logs(), "adaptive", "host")[0]
        self.assertEqual((first["baseline_sample_queued"],
                          first["baseline_sample_added"]), (True, False))

    def test_delayed_confirmation_audit(self):
        audit = records(self.training_logs(), "baseline")
        self.assertEqual((len(audit), audit[0]["original_sample_ts"],
                          audit[0]["ts"]), (65, 60.0, 960.0))

    def test_ready_after_thirty_confirmed_samples(self):
        decision = records(self.training_logs(), "adaptive", "host")[45]
        self.assertEqual((decision["profile_state"],
                          decision["profile_samples_before"]), ("ready", 30))

    def test_history_retains_sixty_samples(self):
        decision = records(self.training_logs(), "adaptive", "host")[-1]
        self.assertEqual(decision["profile_samples_before"], 60)

    def test_ready_threshold_one_mib_boundary(self):
        lines = [host(i, 100000) for i in range(1, 46)]
        data = self.events("ready_boundary", lines + [host(46, 1048575),
                                                       host(47, 1048576)])
        self.assertEqual([(r["threshold_bytes"], r["adaptive_candidate"])
                          for r in records(data, "adaptive", "host")[-2:]],
                         [(1048576, False), (1048576, True)])

    def test_ready_dynamic_median_threshold_boundary(self):
        lines = [host(i, 400000) for i in range(1, 46)]
        data = self.events("dynamic_threshold", lines + [host(46, 1599999),
                                                         host(47, 1600000)])
        self.assertEqual([(r["threshold_bytes"], r["adaptive_candidate"])
                          for r in records(data, "adaptive", "host")[-2:]],
                         [(1600000, False), (1600000, True)])

    def test_candidate_discards_pending_samples(self):
        lines = [host(i, 100000) for i in range(1, 6)] + [host(6, 4194304)]
        data = self.events("quarantine", lines)
        self.assertEqual([(r["event_type"], r["sample_count"])
                          for r in records(data, "baseline")],
                         [("exfil_baseline_discard", 5)])

    def test_degraded_volume_is_not_confirmed_candidate(self):
        data = self.events("degraded", [host(1, 4194304, eligible=False)])
        decision = records(data, "adaptive", "host")[0]
        self.assertEqual((decision["quality_degraded_volume_candidate"],
                          decision["adaptive_candidate"]), (True, False))


class TestSlow(CountedCase):
    def slow(self, name: str, lines: list[str], scope: str = "host"):
        return records(self.events(name, lines), "slow", scope)[-1]

    def test_ten_windows_above_cumulative_threshold(self):
        last = self.slow("slow_exact", [host(i, 419431) for i in range(1, 11)])
        self.assertEqual((last["rolling_payload_bytes"], last["slow_candidate"]),
                         (4194310, True))

    def test_ten_windows_below_cumulative_threshold(self):
        last = self.slow("slow_below", [host(i, 419430) for i in range(1, 11)])
        self.assertEqual((last["rolling_payload_bytes"], last["slow_candidate"]),
                         (4194300, False))

    def test_eight_active_windows_exact_four_mib(self):
        lines = [host(i, 0) for i in (1, 2)] + [host(i, 524288)
                                                 for i in range(3, 11)]
        last = self.slow("slow_eight", lines)
        self.assertEqual((last["rolling_active_windows"], last["slow_candidate"]),
                         (8, True))

    def test_seven_active_windows_above_four_mib(self):
        lines = [host(i, 600000) for i in range(1, 8)] + [host(i, 0)
                                                          for i in range(8, 11)]
        last = self.slow("slow_seven", lines)
        self.assertEqual((last["rolling_active_windows"], last["slow_candidate"]),
                         (7, False))

    def test_one_mib_window_ceiling_resets(self):
        lines = [host(i, 400000) for i in range(1, 10)] + [host(10, 1048576)]
        last = self.slow("slow_ceiling", lines)
        self.assertEqual((last["reason"], last["slow_candidate"]),
                         ("individual_window_at_or_above_ceiling", False))

    def test_ninety_second_gap_accepted(self):
        lines = [host(i, 419431) for i in range(1, 10)]
        self.assertEqual(self.slow("slow_gap_90", lines + [host(
            10, 419431, stamp=630)])["slow_candidate"], True)

    def test_ninety_one_second_gap_resets(self):
        lines = [host(i, 419431) for i in range(1, 10)]
        last = self.slow("slow_gap_91", lines + [host(10, 419431, stamp=631)])
        self.assertEqual((last["rolling_window_count"], last["slow_candidate"]),
                         (1, False))

    def test_forty_nine_second_span_excluded(self):
        lines = [host(i, 419431) for i in range(1, 10)]
        last = self.slow("slow_span_49", lines + [host(10, 419431, span=49)])
        self.assertEqual((last["profile_state"], last["slow_candidate"]),
                         ("quality_excluded", False))

    def test_seventy_one_second_span_excluded(self):
        lines = [host(i, 419431) for i in range(1, 10)]
        last = self.slow("slow_span_71", lines + [host(10, 419431, span=71)])
        self.assertEqual(last["profile_state"], "quality_excluded")

    def test_degraded_window_resets_slow(self):
        data = self.events("degraded", [host(1, 4194304, eligible=False)])
        self.assertEqual(records(data, "slow", "host")[0]["profile_state"],
                         "quality_excluded")

    def test_continued_candidate_suppressed(self):
        data = self.events("slow_repeat", [host(i, 419431)
                                           for i in range(1, 12)])
        self.assertEqual([(r["slow_candidate"], r["candidate_active"], r["reason"])
                          for r in records(data, "slow", "host")[-2:]],
                         [(True, True, "rolling_volume_above_threshold"),
                          (False, True, "candidate_continues_suppressed")])

    def test_destination_scope_candidate(self):
        lines = [destination(i, 419431, "198.51.100.2")
                 for i in range(1, 11)]
        self.assertEqual(self.slow("slow_destination", lines,
                                   "destination")["slow_candidate"], True)


class TestCapacity(CountedCase):
    def test_host_profile_saturation_characterization(self):
        lines = [host(1, 100000, source="10.20.1.11"),
                 host(1, 100000, source="10.20.1.12"),
                 host(1, 100000, source="10.20.1.13"),
                 host(61, 100000, source="10.20.1.13"),
                 host(62, 100000, source="10.20.1.13")]
        data = self.events("host_capacity", lines,
                           overrides="redef DataExfilAdaptive::max_host_profiles = 2;")
        self.assertEqual([(r["src_ip"], r["profile_state"])
                          for r in records(data, "adaptive", "host")
                          if r["src_ip"] == "10.20.1.13"],
                         [("10.20.1.13", "capacity_exceeded")] * 2
                         + [("10.20.1.13", "training")])

    def test_destination_profile_saturation_characterization(self):
        lines = [destination(1, 100000, "198.51.100.1"),
                 destination(1, 100000, "198.51.100.2"),
                 destination(1, 100000, "198.51.100.3"),
                 destination(61, 100000, "198.51.100.3"),
                 destination(62, 100000, "198.51.100.3")]
        data = self.events("dest_capacity", lines, overrides=(
            "redef DataExfilAdaptive::max_destination_profiles = 2;"))
        self.assertEqual([(r["dest_ip"], r["profile_state"])
                          for r in records(data, "adaptive", "destination")
                          if r["dest_ip"] == "198.51.100.3"],
                         [("198.51.100.3", "capacity_exceeded")] * 2
                         + [("198.51.100.3", "training")])

    def test_destination_key_overflow_excludes_host_window(self):
        lines = [
            'emit_conn("D1",10.20.1.11,198.51.100.1,1024,"SF",T,0,F);',
            'emit_conn("D2",10.20.1.11,198.51.100.2,1024,"SF",T,0,F);',
            'emit_conn("D3",10.20.1.11,198.51.100.3,1024,"SF",T,0,F);',
        ]
        data = self.events("destination_key_overflow", lines,
                           overrides="redef DataExfilWindow::max_destination_keys = 2;")
        window = records(data, "host_window")[0]
        self.assertEqual((len(records(data, "destination_window")),
                          window["destination_tracking_overflow_flows"],
                          window["baseline_sample_eligible"]), (2, 1, False))

    def test_host_capacity_after_timed_inactivity(self):
        assert HARNESS is not None
        data = HARNESS.run_script(
            "timed_host_capacity", timed_capacity_script("host"),
            pcap=heartbeat_pcap(), ignore_checksums=True,
        )
        adaptive = records(data, "adaptive", "host")
        slow = records(data, "slow", "host")
        self.assertEqual(
            [(r["src_ip"], r["profile_state"]) for r in adaptive],
            [("10.20.1.11", "training"),
             ("10.20.1.12", "capacity_exceeded"),
             ("10.20.1.12", "training")],
        )
        self.assertEqual(
            [(r["src_ip"], r["profile_state"]) for r in slow],
            [("10.20.1.11", "warming"),
             ("10.20.1.12", "capacity_exceeded"),
             ("10.20.1.12", "warming")],
        )

    def test_destination_capacity_after_timed_inactivity(self):
        assert HARNESS is not None
        data = HARNESS.run_script(
            "timed_dest_capacity", timed_capacity_script("destination"),
            pcap=heartbeat_pcap(), ignore_checksums=True,
        )
        adaptive = records(data, "adaptive", "destination")
        slow = [r for r in records(data, "slow", "destination")
                if not r["synthetic_idle_window"]]
        self.assertEqual(
            [(r["dest_ip"], r["profile_state"]) for r in adaptive],
            [("198.51.100.1", "training"),
             ("198.51.100.2", "capacity_exceeded"),
             ("198.51.100.2", "training")],
        )
        self.assertEqual(
            [(r["dest_ip"], r["profile_state"]) for r in slow],
            [("198.51.100.1", "warming"),
             ("198.51.100.2", "capacity_exceeded"),
             ("198.51.100.2", "warming")],
        )


class TestNativeSchemas(CountedCase):
    """Compare representative rows with the observed M3.4c snapshot."""

    def test_representative_native_json_keys(self):
        expected = json.loads(Path(__file__).with_name(
            "observed_json_schema.json").read_text(encoding="utf-8"))
        sources = {
            "data_exfil_flow": self.events("connection_events", CONNECTION_EVENTS),
            "data_exfil_host_window": self.events("connection_events", CONNECTION_EVENTS),
            "data_exfil_destination_window": self.events("connection_events", CONNECTION_EVENTS),
            "data_exfil_adaptive": self.events(
                "training", [host(i, 100000) for i in range(1, 81)]),
            "data_exfil_baseline": self.events(
                "training", [host(i, 100000) for i in range(1, 81)]),
            "data_exfil_slow": self.events(
                "slow_exact", [host(i, 419431) for i in range(1, 11)]),
        }
        for stream, logs in sources.items():
            first = logs[stream + ".log"][0]
            self.assertEqual(sorted(first), expected[stream], stream)


class TestOfflinePcap(CountedCase):
    def test_generated_tcp_capture_matches_validated_fixture(self):
        self.assertEqual(hashlib.sha256(synthetic_tcp_pcap()).hexdigest(),
                         "a57c0a0d36dd2bd8977cd82ec33afe090912b8e9c5ea01655cef524debb5d5f1")

    def test_packet_analysis_produces_sf_connection_and_flow(self):
        assert HARNESS is not None
        data = HARNESS.run_script(
            "offline_tcp", "@load policy/tuning/json-logs\n",
            pcap=synthetic_tcp_pcap(), ignore_checksums=True,
        )
        conn = data.get("conn.log", [])
        flow = records(data, "flow")
        self.assertEqual((len(conn), len(flow), conn[0]["conn_state"],
                          conn[0]["orig_bytes"], flow[0]["outbound_payload_bytes"],
                          conn[0]["uid"] == flow[0]["uid"]),
                         (1, 1, "SF", 1024, 1024, True))

    def test_generated_heartbeat_matches_validated_fixture(self):
        self.assertEqual(hashlib.sha256(heartbeat_pcap()).hexdigest(),
                         "079954e7b6fa7986c87ab1d9f1751fd227e69fd2ffafc09220db900edd385729")

    def test_host_state_expires_after_idle_window(self):
        assert HARNESS is not None
        script = (EVENT_HELPERS + "\nglobal seed: event();\n"
                  "event zeek_init() &priority=-5\n"
                  "    { schedule 1sec { seed() }; }\n"
                  "event seed()\n"
                  '    { emit_conn("EXPIRY-SEED",10.20.1.11,198.51.100.2,1024,"SF",T,0,F); }\n')
        data = HARNESS.run_script("window_expiry", script,
                                  pcap=heartbeat_pcap(), ignore_checksums=True)
        windows = records(data, "host_window")
        self.assertEqual((len(windows), windows[0]["ts"], windows[-1]["ts"]),
                         (31, 61.0, 1861.0))
