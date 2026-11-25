# Telemetry Quality Gate — BlueGuard v0.5.0-rc4

**Release checkpoint:** 24 November 2026, main Service validated at 18:40:40 UTC; final post-Canary status at 18:41:45 UTC. This is a deployed laboratory release, not a production-ready security product. The complete rc4 source is not bundled; see [source inventory](source-availability.md).

## Purpose and API contract

`GET /api/v1/telemetry/quality` combines the existing telemetry assessments. `policy_version=1`, `scope=available_zeek_snapshot`, `sensor_connectivity=unknown`. The response includes `quality_status`, `capture_fidelity`, `reasons`, and the complete nested `snapshot`, `publisher` and `ingestion` models. Evaluation is in-process and read-only; no external HTTP round trips, AWS calls or automatic suppression of security alerts.

| Input | Existing endpoint | Policy signal |
|---|---|---|
| Snapshot | `/api/v1/telemetry/health` | `fresh`, `stale`, `unavailable`; 900 s threshold; file and latest-event age |
| Publisher | `/api/v1/telemetry/publisher` | `healthy`, `stale`, `unavailable`; 300 s success threshold |
| Ingestion | `/api/v1/telemetry/ingestion` | `recent`, `stale`, `unavailable`; 900 s batch threshold |
| Capture evidence | Snapshot record count, complete `missed_bytes` and sum | `no_observed_gaps`, `gaps_observed`, `unknown` |

### Deterministic policy v1

Precedence: `critical` > `degraded` > `unknown` > `healthy`.

- **Critical:** a fresh snapshot with positive aggregate missed bytes and complete evidence.
- **Degraded:** at least one stale component, unless critical takes precedence. A stale snapshot with historical gaps remains degraded; it is not an assertion of current packet loss.
- **Unknown:** unavailable health component or insufficient capture evidence, absent higher-priority evidence. Empty or incomplete snapshots must not be interpreted as gap-free.
- **Healthy:** fresh snapshot, nonempty complete capture evidence with no observed gaps, healthy publisher and recent ingestion.

Capture fidelity is independent of overall quality. The snapshot-wide aggregate does not identify when each gap occurred. Freshness is not a per-gap time window; completeness of `missed_bytes` fields is not completeness of packet capture. The reads of the three components are not a single atomic transaction, and inactivity may cause stale event/batch states even if the host is functioning.

Reason codes in the deployed policy: `snapshot_stale`, `snapshot_unavailable`, `snapshot_gaps_observed`, `capture_evidence_unavailable`, `publisher_stale`, `publisher_unavailable`, `ingestion_stale`, `ingestion_unavailable`.

## Dashboard

The new panel is placed before Telemetry Health. It displays overall classification, component statuses, missed bytes, capture fidelity, unknown sensor connectivity and human-readable reasons. The JS validates the response, polls every 60 s when visible, supports manual refresh and aborts pending HTTP requests after 10 s. It distinguishes a backend `unknown` assessment from an API request failure and clears values to `n/d` on failure. The frontend does not independently calculate the quality policy.

## Observed main-Service result

| Field | Value at approximately 18:40:40 UTC |
|---|---|
| Quality status / capture fidelity | `degraded` / `gaps_observed` |
| Snapshot records | 11 |
| Snapshot age / latest-event age | 2,319 s / 2,459 s |
| Total `missed_bytes` / complete | 9,136,929 / true |
| Publisher status / last success age | `healthy` / 37 s |
| Ingestion status / last batch age | `stale` / 2,374 s |
| Last accepted batch | 5 new, 0 duplicates, 11 total |
| Sensor connectivity | `unknown` |
| Reasons | `snapshot_stale`, `snapshot_gaps_observed`, `ingestion_stale` |

The release succeeds because the classification matches available evidence, not because the telemetry happens to be healthy.

## Release verification

| Stage | Observed result |
|---|---|
| QA | 54/54 tests passed; 1 Starlette deprecation warning; final run 1.14 s |
| File permissions | New source/test files made readable to UID 10001 (0644); no broad permission changes |
| UI regression | Scoped ingestion assertion to Telemetry Health section; retained the structural check |
| Build | Offline incremental rc3-based image; 24/24 source/demo file SHA-256 checks passed |
| Smoke test | FastAPI 0.163.1, UID 10001, rc4, six required GET routes via OpenAPI |
| Containerd | rc4 imported, rc3 retained |
| Canary | `blueguard-api-canary` 1/1 Ready, distinct app label; main EndpointSlice contained only rc3 Pod |
| API | Seven endpoints succeeded on Canary and then main Service |
| Promotion / cleanup | Rolling update successful; Canary deleted; main Pod 1/1 Ready, zero restarts |

The three UI tests are HTTP/static smoke tests, not browser execution tests. Browser visualization was reported in the session; the manual refresh HTTP transaction and JavaScript syntax check are not independently confirmed in the retained outputs (Node.js not installed). No new MTU experiment or Traffic Mirroring activation was required for this release. No AWS shutdown was confirmed after the final check.

Image manifest digest: `sha256:93f833b320aaaaeac0e36ecabb458d3c796e438ed08c504294a83ff7d2192689`.

The development tree and rollback source remain on the Control Plane. See [verification](verification.md), [operations](operations.md) and [selected evidence](../evidence/2026-11-24/result.json).

## Next release

CloudWatch monitoring remains planned for rc5; it must distinguish observed skip metrics from missing data and current session inventory without treating either as a proof of capture completeness. See [roadmap](roadmap.md).
