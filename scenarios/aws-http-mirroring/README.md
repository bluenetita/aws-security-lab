# AWS HTTP traffic-mirroring experiments

A dedicated EC2 Worker sent controlled HTTP traffic while Zeek observed a copy of selected network packets through AWS Traffic Mirroring over VXLAN/UDP 4789.

| Test | Outcome |
|---|---|
| 16 November smoke test | 3/3 HTTP 200 responses and corresponding Zeek HTTP records |
| LIVE-AD-03 | 5 MiB at 256 KiB/s, 247 mirror-skipped outbound packets, Zeek `missed_bytes=357160` |
| LIVE-AD-04 | 5 MiB at 64 KiB/s, 3 mirror-skipped outbound packets, Zeek `missed_bytes=4344` |
| LIVE-AD-05 | 5 MiB at 32 KiB/s, Zeek connection UID `CQN9op1cWFef1nHdCj` with `missed_bytes=0` |

Full measurements and interpretation: [experimental results](../../docs/experimental-results.md). Structured observations: [`evidence/`](../../evidence/).

**Scope:** test payloads and measured network telemetry only; not a claim of attack detection or representative production traffic. The VPC mirror session was temporary and was removed after tests. Do not leave Traffic Mirroring enabled without an approved monitoring plan.
