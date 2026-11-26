"""Offline Zeek 9.0.1 fixtures derived from the M3.4c synthetic harness.

Every Zeek process reads a generated PCAP. It never opens a live interface.
Generated scripts, captures, and logs live under a TemporaryDirectory.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import struct
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY = REPO_ROOT / "blue-team/zeek/site/blueguard_exfil/__load__.zeek"
EXPECTED_VERSION = "9.0.1"
ZEEK = Path(os.environ.get("BLUEGUARD_ZEEK", "/opt/zeek/bin/zeek"))

# The event constructors and packet bytes preserve the validated M3.4c logic.
EVENT_HELPERS = r"""
@load policy/tuning/json-logs
function emit_host_with_flows(stamp: time, source: addr, volume: count,
                              eligible: bool, span: interval, flows: count,
                              close_tick: bool)
    {
    local r: DataExfilWindow::WindowInfo = [
      $ts=stamp, $event_type="synthetic_host_window",
      $src_ip=source, $window_start=stamp-span,
      $window_seconds=span, $first_window_partial=F,
      $flow_count=flows,
      $outbound_payload_bytes=volume, $max_single_flow_bytes=volume,
      $top_dest_ip=198.51.100.2, $top_dest_bytes=volume,
      $top_dest_share_percent=(volume > 0 ? 100 : 0),
      $tracked_destination_payload_bytes=volume,
      $unattributed_payload_bytes=0, $attribution_complete=T,
      $capture_gap_flows=(eligible ? 0 : 1), $non_sf_flows=0,
      $missing_outbound_byte_estimates=0,
      $destination_tracking_overflow_flows=0,
      $baseline_sample_eligible=eligible, $window_invariant_ok=T,
      $byte_basis="synthetic", $aggregation_scope="direct_event_test",
      $note="synthetic event injection"
    ];
    event DataExfilWindow::host_window_ready(r);
    if ( close_tick )
        event DataExfilWindow::window_tick_complete(stamp,span);
    }
function emit_host(stamp: time, source: addr, volume: count, eligible: bool, span: interval)
    {
    emit_host_with_flows(stamp, source, volume, eligible, span,
                         (volume > 0 ? 1 : 0), T);
    }
function emit_dest_with_flows(stamp: time, source: addr, dest: addr,
                              volume: count, eligible: bool, flows: count,
                              close_tick: bool)
    {
    local r: DataExfilWindow::DestinationWindowInfo = [
      $ts=stamp, $event_type="synthetic_dest_window",
      $src_ip=source, $dest_ip=dest, $window_start=stamp-60secs,
      $window_seconds=60secs, $destination_payload_bytes=volume,
      $destination_flow_count=flows,
      $host_outbound_payload_bytes=volume,
      $host_flow_count=flows,
      $first_window_partial=F,
      $capture_gap_flows_destination=(eligible ? 0 : 1),
      $non_sf_flows_destination=0,
      $missing_outbound_byte_estimates_destination=0,
      $capture_gap_flows_host=(eligible ? 0 : 1),
      $non_sf_flows_host=0, $missing_outbound_byte_estimates_host=0,
      $destination_tracking_overflow_flows_host=0,
      $window_invariant_ok=T, $baseline_sample_eligible=eligible,
      $byte_basis="synthetic", $aggregation_scope="direct_event_test",
      $note="synthetic event injection"
    ];
    event DataExfilWindow::destination_window_ready(r);
    if ( close_tick )
        event DataExfilWindow::window_tick_complete(stamp,60secs);
    }
function emit_dest(stamp: time, source: addr, dest: addr, volume: count, eligible: bool)
    {
    emit_dest_with_flows(stamp, source, dest, volume, eligible,
                         (volume > 0 ? 1 : 0), T);
    }
function emit_conn(uid: string, source: addr, dest: addr, volume: count,
                   state: string, has_bytes: bool, missed: count, external: bool)
    {
    local r: Conn::Info = [
      $ts=network_time(), $uid=uid,
      $id=[$orig_h=source, $orig_p=12345/tcp,
           $resp_h=dest, $resp_p=443/tcp],
      $proto=tcp, $conn_state=state, $missed_bytes=missed
    ];
    if ( has_bytes )
        {
        if ( external )
            { r$orig_bytes=0; r$resp_bytes=volume; }
        else
            { r$orig_bytes=volume; r$resp_bytes=0; }
        }
    event Conn::log_conn(r);
    }
"""


def host(index: int, volume: int, source: str = "10.20.1.11", *,
         eligible: bool = True, span: int = 60, stamp: int | None = None,
         flow_count: int | None = None, close_tick: bool = True) -> str:
    stamp = index * 60 if stamp is None else stamp
    if flow_count is not None or not close_tick:
        flows = (1 if volume > 0 else 0) if flow_count is None else flow_count
        return (f"emit_host_with_flows(network_time()+{stamp}secs, {source}, "
                f"{volume}, {'T' if eligible else 'F'}, {span}secs, {flows}, "
                f"{'T' if close_tick else 'F'});")
    return (f"emit_host(network_time()+{stamp}secs, {source}, {volume}, "
            f"{'T' if eligible else 'F'}, {span}secs);")


def destination(index: int, volume: int, dest: str, *,
                source: str = "10.20.1.11", eligible: bool = True,
                stamp: int | None = None, flow_count: int | None = None,
                close_tick: bool = True) -> str:
    stamp = index * 60 if stamp is None else stamp
    if flow_count is not None or not close_tick:
        flows = (1 if volume > 0 else 0) if flow_count is None else flow_count
        return (f"emit_dest_with_flows(network_time()+{stamp}secs, {source}, "
                f"{dest}, {volume}, {'T' if eligible else 'F'}, {flows}, "
                f"{'T' if close_tick else 'F'});")
    return (f"emit_dest(network_time()+{stamp}secs, {source}, {dest}, "
            f"{volume}, {'T' if eligible else 'F'});")


def records(logs: dict[str, list[dict]], stem: str,
            scope: str | None = None) -> list[dict]:
    rows = logs.get(f"data_exfil_{stem}.log", [])
    return [row for row in rows if scope is None or row.get("scope") == scope]


def _ethernet_ipv4(source: str, dest: str, proto: int, body: bytes) -> bytes:
    orig = ipaddress.IPv4Address(source).packed
    resp = ipaddress.IPv4Address(dest).packed
    ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(body), 1, 0,
                     64, proto, 0, orig, resp)
    ethernet = (b"\x02\x00\x00\x00\x00\x02"
                + b"\x02\x00\x00\x00\x00\x01" + b"\x08\x00")
    return ethernet + ip + body


def _tcp(source: str, dest: str, sport: int, dport: int,
         seq: int, ack: int, flags: int, payload: bytes = b"") -> bytes:
    header = struct.pack("!HHIIHHHH", sport, dport, seq, ack,
                         (5 << 12) | flags, 65535, 0, 0)
    return _ethernet_ipv4(source, dest, 6, header + payload)


def _pcap(frames: list[tuple[int, bytes]]) -> bytes:
    out = bytearray(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
    for timestamp, frame in frames:
        out.extend(struct.pack("<IIII", timestamp, 0, len(frame), len(frame)))
        out.extend(frame)
    return bytes(out)


def synthetic_tcp_pcap() -> bytes:
    """Eight synthetic packets: handshake, 1024-byte payload, FIN close."""
    source, dest = "10.20.1.11", "198.51.100.2"
    packets = [
        _tcp(source, dest, 12345, 443, 1000, 0, 0x02),
        _tcp(dest, source, 443, 12345, 2000, 1001, 0x12),
        _tcp(source, dest, 12345, 443, 1001, 2001, 0x10),
        _tcp(source, dest, 12345, 443, 1001, 2001, 0x18, b"A" * 1024),
        _tcp(dest, source, 443, 12345, 2001, 2025, 0x10),
        _tcp(source, dest, 12345, 443, 2025, 2001, 0x11),
        _tcp(dest, source, 443, 12345, 2001, 2026, 0x11),
        _tcp(source, dest, 12345, 443, 2026, 2002, 0x10),
    ]
    return _pcap(list(enumerate(packets, 1)))


def heartbeat_pcap() -> bytes:
    """83 synthetic UDP timestamps, one per minute through minute 82."""
    udp = struct.pack("!HHHH", 5000, 5001, 9, 0) + b"x"
    frame = _ethernet_ipv4("203.0.113.1", "203.0.113.2", 17, udp)
    return _pcap([(1 + index * 60, frame) for index in range(83)])


def timed_capacity_script(scope: str) -> str:
    """Admit one identity, probe at 2 minutes, then again at 80 minutes.

    Both adaptive and slow limits are reduced to one only in this fixture.
    The source addresses in the host case are injected directly into the
    window callback; the fixture does not claim packet-level eligibility.
    """
    if scope == "host":
        tuning = ("redef DataExfilSlow::maximum_host_profiles = 1;\n"
                  "redef DataExfilAdaptive::max_host_profiles = 1;")
        first = "emit_host(network_time(),10.20.1.11,100000,T,60secs);"
        second = "emit_host(network_time(),10.20.1.12,100000,T,60secs);"
    elif scope == "destination":
        tuning = ("redef DataExfilSlow::maximum_destination_profiles = 1;\n"
                  "redef DataExfilAdaptive::max_destination_profiles = 1;")
        first = "emit_dest(network_time(),10.20.1.11,198.51.100.1,100000,T);"
        second = "emit_dest(network_time(),10.20.1.11,198.51.100.2,100000,T);"
    else:
        raise ValueError(f"Unknown profile scope: {scope}")
    return (EVENT_HELPERS + "\n" + tuning
            + "\nglobal seed: event();\n"
            + "global early_probe: event();\n"
            + "global late_probe: event();\n"
            + "event zeek_init() &priority=-5\n    {\n"
            + "    schedule 1sec { seed() };\n"
            + "    schedule 2mins { early_probe() };\n"
            + "    schedule 80mins { late_probe() };\n    }\n"
            + f"event seed()\n    {{ {first} }}\n"
            + f"event early_probe()\n    {{ {second} }}\n"
            + f"event late_probe()\n    {{ {second} }}\n")


class ZeekHarness:
    """Run the recovered policy with generated inputs and parse native logs."""

    def __init__(self) -> None:
        if not hasattr(os, "geteuid") or os.geteuid() == 0:
            raise RuntimeError("Zeek policy tests require a non-root Linux user")
        if not ZEEK.is_absolute():
            raise RuntimeError("BLUEGUARD_ZEEK must be an absolute executable path")
        if not POLICY.is_file():
            raise RuntimeError(f"BlueGuard policy missing: {POLICY}")
        self.temp = tempfile.TemporaryDirectory(prefix="blueguard-zeek-policy-")
        self.root = Path(self.temp.name)
        self.empty_pcap = self.root / "empty.pcap"
        self.empty_pcap.write_bytes(_pcap([]))
        self.cache: dict[str, dict[str, list[dict]]] = {}
        try:
            result = self._invoke([str(ZEEK), "--version"], self.root)
            match = re.search(r"\bversion\s+(\d+\.\d+\.\d+)\b", result.stdout)
            if not match or match.group(1) != EXPECTED_VERSION:
                raise RuntimeError(
                    f"Zeek {EXPECTED_VERSION} required; got {result.stdout.strip()!r}"
                )
            self.version = match.group(1)
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def _invoke(command: list[str], directory: Path) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["ZEEK_DNS_FAKE"] = "1"
        try:
            result = subprocess.run(
                command, cwd=directory, env=environment, text=True,
                capture_output=True, timeout=30, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"Zeek command failed in {directory}: {command!r}: {exc}") from exc
        if result.returncode != 0:
            raise RuntimeError(
                f"Zeek exit {result.returncode} in {directory}: {command!r}\n"
                f"stdout:\n{result.stdout[-4000:]}\nstderr:\n{result.stderr[-4000:]}"
            )
        return result

    def parse_policy(self) -> None:
        self._invoke([str(ZEEK), "-a", str(POLICY)], self.root)

    def run_script(self, name: str, script: str, *, pcap: bytes | None = None,
                   ignore_checksums: bool = False) -> dict[str, list[dict]]:
        if name in self.cache:
            return self.cache[name]
        directory = self.root / name
        directory.mkdir()
        driver = directory / "driver.zeek"
        driver.write_text(script, encoding="utf-8")
        capture = directory / "synthetic.pcap"
        capture.write_bytes(self.empty_pcap.read_bytes() if pcap is None else pcap)
        self._invoke([str(ZEEK), "-a", str(POLICY), str(driver)], directory)
        command = [str(ZEEK), "-D"]
        if ignore_checksums:
            command.append("-C")
        command += ["-r", str(capture), str(POLICY), str(driver)]
        self._invoke(command, directory)
        logs: dict[str, list[dict]] = {}
        for path in directory.glob("*.log"):
            try:
                logs[path.name] = [json.loads(line) for line in path.read_text(
                    encoding="utf-8").splitlines() if line]
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"Invalid native JSON log {path}: {exc}") from exc
        self.cache[name] = logs
        return logs

    def run_events(self, name: str, lines: list[str], *,
                   overrides: str = "") -> dict[str, list[dict]]:
        body = "\n".join(f"    {line}" for line in lines)
        script = (EVENT_HELPERS + "\n" + overrides
                  + "\nevent zeek_init() &priority=-5\n    {\n"
                  + body + "\n    }\n")
        return self.run_script(name, script)
