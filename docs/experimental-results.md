# Experimental results

**Purpose:** document observed results of controlled AWS Traffic Mirroring and BlueGuard integration tests, without inferring attack detection or production performance.

## HTTP observation, 16 November 2026

Three HTTP GET requests from the Worker were captured and represented in Zeek JSON logs. All three requests returned HTTP 200, and the extracted records matched the selected host/URI tests. Supporting data: [`evidence/2026-11-16/`](../evidence/2026-11-16/).

## LIVE-AD-03 / LIVE-AD-04 / LIVE-AD-05

The controlled workload uploaded a synthetic **5 MiB (5,242,880 B)** payload from the Worker (`10.20.1.11`) to the Control Plane (`10.20.1.10:18080`). The server verified the received payload. Network metrics and Zeek values are distinct measurements.

| Measurement | LIVE-AD-03 | LIVE-AD-04 | LIVE-AD-05 |
|---|---:|---:|---:|
| Date (UTC) | 18 Nov | 18 Nov | 19 Nov |
| HTTP rate limit | 256 KiB/s | 64 KiB/s | 32 KiB/s |
| Observed duration | 20.004 s | 80.042 s | 160.079 s (Zeek duration) |
| HTTP response / payload check | 200 / verified | 200 / verified | Controlled transfer confirmed |
| Worker outbound packets | 3,684 | 3,685 | Not independently available in repository |
| Mirrored outbound packets (AWS) | 3,437 | 3,682 | Not independently available in repository |
| AWS outbound skipped packets | **247** | **3** | Not independently available in repository |
| AWS inbound skipped packets | **0** | **1** | Not independently available in repository |
| Zeek `missed_bytes` | **357,160** | **4,344** | **0** |
| Zeek connection state | `SF` | `SF` | `SF` |
| Zeek UID | `C9x8Ct3NgkfJVcOP5a` | `CKbTa21kFNwV3njJV5` | `CQN9op1cWFef1nHdCj` |

### Interpretation

- LIVE-AD-03/04 showed **packet loss in the mirrored copy**, even though the original HTTP transfer succeeded.
- At the lower tested rate, observed mirror skips and Zeek missing bytes were smaller. This correlation **does not establish** throughput as the sole cause; other conditions may differ.
- In LIVE-AD-05, Zeek reported `missed_bytes=0` **for that TCP connection**. This is not a guarantee of zero packet loss across the sensor or future workloads.
- Zeek `orig_bytes=5,243,137` in LIVE-AD-05 includes protocol/application framing relative to the 5 MiB test payload; it is not a file-integrity hash.

**LIVE-AD-05 detailed Zeek fields:** source port `34588`, destination port `18080`, protocol `tcp`, service `http`, `orig_pkts=3687`, `resp_pkts=969`, `resp_bytes=369`, duration `160.0792109966278 s`.

Data: [`evidence/2026-11-18/result.json`](../evidence/2026-11-18/result.json) and [`evidence/2026-11-19/result.json`](../evidence/2026-11-19/result.json). The evidence files are structured transcriptions of terminal results, not exported PCAP files or raw CloudWatch datasets.

## SSH ingestion and persistence, 19 November

| Test | Observed result |
|---|---|
| SSH receiver health | `BLUEGUARD_RECEIVER_READY` |
| Unauthorized SSH command | Rejected, exit status 126 |
| First insertion | `OK new=1 duplicates=0 total=1` |
| Repeated insertion | `OK new=0 duplicates=1 total=1` |
| Collector unit tests | **8/8 passed** |
| SSH failure/recovery | Checkpoint did not advance on failed transfer; successful retry was acknowledged |
| Simulated rotation | Partial line, completion, `.gz` archive and new current file handled |
| Collector timer | Automatic invocation recorded at 16:42:25 UTC |
| Publisher timer | Automatic invocation recorded at 16:53:08 UTC |
| Publisher store | Byte-for-byte comparison and read-only Pod access verified |

The deduplication key was `(uid, ts)`. Acknowledged delivery and retry support reduce data-loss risk; they do not establish general exactly-once semantics across all failure modes.

## Kubernetes and UI, 19 November

The `blueguard-api` Deployment rolled out image **`localhost/blueguard-api:0.4.2`** successfully: one Pod ready, zero restarts at observation. `GET /healthz` and `GET /readyz` succeeded; `GET /api/v1/status` returned `0.4.2-lab`; `GET /api/v1/zeek/connections` returned **one** genuine Zeek connection, UID `CQN9op1cWFef1nHdCj`, with `live=false`.

A separate Podman preview used synthetic JSONL fixtures and demonstrated API access to **three** records and their display in the browser. This preview **does not** constitute a new end-to-end traffic-mirroring result. The dashboard's **seven alert records remain synthetic**.

## Outstanding experiment

A **new** mirrored connection captured *after the v0.4.2 rollout*, observed through the collector/receiver/publisher and appearing in the Kubernetes browser without manual file edits, has **not** been validated. End-to-end latency, longer-term reliability and Wazuh-based detection have therefore not been measured.
