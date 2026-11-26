"""Focused BG-BUG-003 expiration, audit, and learning-safety regressions."""

import json
import unittest
from pathlib import Path

from _support import ZeekHarness, destination, host, records


SHORT_EXPIRY = "redef DataExfilAdaptive::profile_idle_expiry = 120secs;"
ONE_HOST = SHORT_EXPIRY + "\nredef DataExfilAdaptive::max_host_profiles = 1;"
ONE_DEST = SHORT_EXPIRY + "\nredef DataExfilAdaptive::max_destination_profiles = 1;"


def tick(stamp: int) -> str:
    return ("event DataExfilWindow::window_tick_complete("
            f"network_time()+{stamp}secs,60secs);")


class AdaptiveLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = ZeekHarness()

    @classmethod
    def tearDownClass(cls):
        cls.harness.close()

    def run_case(self, name, lines, overrides=SHORT_EXPIRY):
        return self.harness.run_events(name, lines, overrides=overrides)

    def test_exact_ttl_discards_pending_before_any_commit(self):
        data = self.run_case("exact_ttl", [host(1, 100000), tick(179), tick(180)])
        audit = records(data, "baseline")
        self.assertEqual([(r["event_type"], r["ts"], r["sample_count"],
                           r["sample_bytes"], r["original_sample_ts"])
                          for r in audit],
                         [("exfil_baseline_discard", 180.0, 1, 100000, 180.0),
                          ("exfil_baseline_profile_expired", 180.0, 0, 0, 60.0)])
        observed = json.loads(Path(__file__).with_name(
            "observed_json_schema.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(audit[-1]), observed["data_exfil_baseline"])

    def test_one_second_before_boundary_retains_profile(self):
        data = self.run_case("pre_boundary", [host(1, 100000), tick(179)])
        self.assertEqual([r for r in records(data, "baseline")
                          if r["event_type"] == "exfil_baseline_profile_expired"], [])

    def test_zero_payload_real_flow_refreshes_existing_profile(self):
        data = self.run_case("zero_payload_activity", [
            host(1, 100000),
            host(3, 0, flow_count=1, close_tick=False), tick(180), tick(299),
            tick(300),
        ])
        expired = [r for r in records(data, "baseline")
                   if r["event_type"] == "exfil_baseline_profile_expired"]
        self.assertEqual([(r["ts"], r["original_sample_ts"]) for r in expired],
                         [(300.0, 180.0)])

    def test_zero_payload_destination_flow_refreshes_existing_profile(self):
        data = self.run_case("zero_payload_destination", [
            destination(1, 100000, "198.51.100.2"),
            destination(3, 0, "198.51.100.2", flow_count=1,
                        close_tick=False),
            tick(180), tick(299), tick(300),
        ])
        expired = [r for r in records(data, "baseline")
                   if r["event_type"] == "exfil_baseline_profile_expired"]
        self.assertEqual([(r["scope"], r["ts"], r["original_sample_ts"])
                          for r in expired],
                         [("destination", 300.0, 180.0)])

    def test_idle_host_callback_does_not_refresh_activity(self):
        data = self.run_case("idle_callback", [host(1, 100000), host(2, 0),
                                               tick(180)])
        expired = [r for r in records(data, "baseline")
                   if r["event_type"] == "exfil_baseline_profile_expired"]
        self.assertEqual([(r["ts"], r["original_sample_ts"]) for r in expired],
                         [(180.0, 60.0)])

    def test_degraded_observed_flow_refreshes_without_learning(self):
        data = self.run_case("degraded_activity", [
            host(1, 100000), host(3, 100000, eligible=False), tick(299), tick(300),
        ])
        audit = records(data, "baseline")
        self.assertEqual([(r["event_type"], r["ts"], r["reason"])
                          for r in audit],
                         [("exfil_baseline_discard", 180.0, "quality_reset"),
                          ("exfil_baseline_profile_expired", 300.0,
                           "profile_idle_expired")])
        decision = records(data, "adaptive", "host")[-1]
        self.assertEqual((decision["sample_eligible"],
                          decision["baseline_sample_queued"]), (False, False))

    def test_excluded_large_flow_refreshes_activity(self):
        data = self.run_case("excluded_large_activity", [
            host(1, 100000), host(3, 3145728), tick(299), tick(300),
        ])
        expired = [r for r in records(data, "baseline")
                   if r["event_type"] == "exfil_baseline_profile_expired"]
        self.assertEqual([(r["ts"], r["original_sample_ts"]) for r in expired],
                         [(300.0, 180.0)])
        self.assertEqual(records(data, "adaptive", "host")[-1]["reason"],
                         "large_untrusted_sample_excluded_from_training")

    def test_candidate_reload_preserves_activity_and_source_hold(self):
        data = self.run_case("candidate_activity", [
            host(1, 100000), host(2, 4194304), tick(239), tick(240),
            host(5, 100000), host(13, 100000),
        ])
        expired = [r for r in records(data, "baseline")
                   if r["event_type"] == "exfil_baseline_profile_expired"]
        self.assertEqual([(r["ts"], r["original_sample_ts"]) for r in expired],
                         [(240.0, 120.0)])
        decisions = records(data, "adaptive", "host")
        self.assertEqual((decisions[-2]["reason"],
                          decisions[-1]["reason"],
                          decisions[-1]["profile_samples_before"]),
                         ("learning_suspended_by_rolling_or_volume_candidate",
                          "baseline_learning_pending", 0))

    def test_capacity_rejection_before_barrier_then_admission(self):
        data = self.run_case("barrier_admission", [
            host(1, 100000, source="10.20.1.11"),
            host(3, 100000, source="10.20.1.12", close_tick=False),
            tick(180), host(4, 100000, source="10.20.1.12"),
        ], ONE_HOST)
        rows = [r for r in records(data, "adaptive", "host")
                if r["src_ip"] == "10.20.1.12"]
        self.assertEqual([(r["ts"], r["profile_state"],
                           r["profile_samples_before"]) for r in rows],
                         [(180.0, "capacity_exceeded", 0),
                          (240.0, "training", 0)])

    def test_existing_activity_after_new_callback_retains_profile(self):
        self._assert_current_tick_retention("new_before_existing", reverse=True)

    def test_existing_activity_before_new_callback_retains_profile(self):
        self._assert_current_tick_retention("existing_before_new", reverse=False)

    def _assert_current_tick_retention(self, name, *, reverse):
        active = host(3, 0, source="10.20.1.11", flow_count=1,
                      close_tick=False)
        newcomer = host(3, 100000, source="10.20.1.12", close_tick=False)
        pair = [newcomer, active] if reverse else [active, newcomer]
        data = self.run_case(name, [host(1, 100000), *pair, tick(180)], ONE_HOST)
        new = [r for r in records(data, "adaptive", "host")
               if r["src_ip"] == "10.20.1.12"]
        self.assertEqual([r["profile_state"] for r in new], ["capacity_exceeded"])
        self.assertEqual([r for r in records(data, "baseline")
                          if r["event_type"] == "exfil_baseline_profile_expired"], [])

    def test_host_and_destination_expire_independently(self):
        data = self.run_case("independent_scopes", [
            host(1, 100000, close_tick=False),
            destination(1, 100000, "198.51.100.2", close_tick=False), tick(60),
            host(2, 0, flow_count=1, close_tick=False), tick(120),
            tick(180), tick(240),
        ])
        expired = [r for r in records(data, "baseline")
                   if r["event_type"] == "exfil_baseline_profile_expired"]
        self.assertEqual([(r["scope"], r["ts"], r["original_sample_ts"])
                          for r in expired],
                         [("destination", 180.0, 60.0),
                          ("host", 240.0, 120.0)])

    def test_destination_exact_boundary_and_next_callback(self):
        data = self.run_case("dest_boundary", [
            destination(1, 100000, "198.51.100.1"),
            destination(3, 100000, "198.51.100.2", close_tick=False),
            tick(180), destination(4, 100000, "198.51.100.2"),
        ], ONE_DEST)
        rows = [r for r in records(data, "adaptive", "destination")
                if r["dest_ip"] == "198.51.100.2"]
        self.assertEqual([(r["ts"], r["profile_state"])
                          for r in rows],
                         [(180.0, "capacity_exceeded"), (240.0, "training")])

    def test_expiration_when_delayed_learning_disabled(self):
        data = self.run_case("immediate_learning_expiry", [
            host(1, 100000), tick(180),
            host(4, 100000, source="10.20.1.12"),
        ], ONE_HOST + "\nredef DataExfilAdaptive::delayed_learning_enabled = F;")
        audit = records(data, "baseline")
        self.assertEqual([(r["event_type"], r["sample_count"], r["sample_bytes"])
                          for r in audit],
                         [("exfil_baseline_profile_expired", 1, 100000)])
        new = [r for r in records(data, "adaptive", "host")
               if r["src_ip"] == "10.20.1.12"][-1]
        self.assertEqual((new["profile_state"], new["baseline_sample_added"],
                          new["profile_samples_before"]), ("training", True, 0))

    def test_same_identity_relearns_after_confirmed_history_expires(self):
        # Immediate confirmation makes the retired history observable without
        # changing the policy's normal delayed-learning default.
        data = self.run_case("same_identity_fresh_learning", [
            host(1, 100000), tick(180), host(4, 100000), host(5, 100000),
        ], SHORT_EXPIRY +
            "\nredef DataExfilAdaptive::delayed_learning_enabled = F;")
        expired = [r for r in records(data, "baseline")
                   if r["event_type"] == "exfil_baseline_profile_expired"]
        self.assertEqual([(r["scope"], r["src_ip"], r["ts"],
                           r["original_sample_ts"], r["sample_count"],
                           r["sample_bytes"]) for r in expired],
                         [("host", "10.20.1.11", 180.0, 60.0, 1, 100000)])
        decisions = records(data, "adaptive", "host")
        self.assertEqual([(r["ts"], r["src_ip"], r["profile_state"],
                           r["profile_samples_before"], r["baseline_sample_added"])
                          for r in decisions],
                         [(60.0, "10.20.1.11", "training", 0, True),
                          (240.0, "10.20.1.11", "training", 0, True),
                          (300.0, "10.20.1.11", "training", 1, True)])

    def test_repeated_churn_respects_one_profile_limit(self):
        data = self.run_case("repeated_churn", [
            host(1, 100000, source="10.20.1.11"),
            host(3, 100000, source="10.20.1.12", close_tick=False), tick(180),
            host(4, 100000, source="10.20.1.12"),
            host(6, 100000, source="10.20.1.13", close_tick=False), tick(360),
            host(7, 100000, source="10.20.1.13"),
        ], ONE_HOST)
        decisions = [(r["src_ip"], r["profile_state"])
                     for r in records(data, "adaptive", "host")]
        self.assertEqual(decisions,
                         [("10.20.1.11", "training"),
                          ("10.20.1.12", "capacity_exceeded"),
                          ("10.20.1.12", "training"),
                          ("10.20.1.13", "capacity_exceeded"),
                          ("10.20.1.13", "training")])
        self.assertEqual(len([r for r in records(data, "baseline")
                              if r["event_type"] == "exfil_baseline_profile_expired"]), 2)

    def test_untracked_degraded_activity_does_not_allocate(self):
        data = self.run_case("no_extra_allocation", [
            host(1, 100000, source="10.20.1.11", eligible=False),
            host(2, 100000, source="10.20.1.12"),
        ], ONE_HOST)
        self.assertEqual([(r["src_ip"], r["profile_state"])
                          for r in records(data, "adaptive", "host")],
                         [("10.20.1.11", "quality_excluded"),
                          ("10.20.1.12", "training")])

    def test_invalid_zero_expiry_warns_and_disables_eviction(self):
        data = self.run_case("invalid_expiry", [
            host(1, 100000), tick(3600),
            host(61, 100000, source="10.20.1.12"),
        ], "redef DataExfilAdaptive::profile_idle_expiry = 0secs;\n"
           "redef DataExfilAdaptive::max_host_profiles = 1;")
        new = [r for r in records(data, "adaptive", "host")
               if r["src_ip"] == "10.20.1.12"]
        self.assertEqual([r["profile_state"] for r in new],
                         ["capacity_exceeded"])
        self.assertEqual([r for r in records(data, "baseline")
                          if r["event_type"] == "exfil_baseline_profile_expired"], [])
        warnings = data.get("reporter.log", [])
        self.assertEqual(any("profile_idle_expiry must be positive"
                             in r.get("message", "") for r in warnings), True)
