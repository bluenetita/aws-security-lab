# BlueGuard — AWS Network Security Monitoring Lab

BlueGuard is an experimental network-telemetry platform built on **Amazon EC2, k3s Kubernetes and Zeek**. It demonstrates packet mirroring, secure incremental ingestion of Zeek connection records, telemetry-quality assessment and HTTP-based visualization in a containerized dashboard.

**Scope:** controlled cybersecurity laboratory. The recorded evidence does **not** establish a production SIEM, intrusion-detection engine, managed SOC service or customer-ready application.

## Implementation status — 24 November 2026

| Component | Verified implementation | Status |
|---|---|---|
| AWS networking | VPC/subnet, EC2 nodes, Security Groups, temporary Traffic Mirroring | Validated in controlled tests |
| Kubernetes | One API Deployment/Pod and private ClusterIP Service; node-local image | **v0.5.0-rc4 deployed and healthy** at 18:41:45 UTC |
| Zeek | UDP/VXLAN capture, JSON connection logs, compressed archives | Verified; capture completeness is not guaranteed |
| Ingestion | Incremental collector, restricted SSH receiver, deduplication, checkpoint and retry; batch receipt | Verified; latest recorded batch contains 5 new records |
| Publishing | Periodic systemd publisher, validated JSONL snapshot, atomic replacement, read-only volume | Verified; heartbeat healthy at release check |
| Telemetry Quality Gate | Snapshot freshness, publisher and ingestion health, observed TCP gaps | **Implemented and deployed in rc4** |
| AWS CloudWatch integration | Historical manual metric queries; automated collector and endpoint planned | **Planned for rc5; not implemented** |
| Wazuh | Dedicated EC2 resource; no validated BlueGuard integration | **Not integrated** |

The rc4 Canary was removed after promotion; the main Pod was Ready (1/1) with zero restarts. Both rc3 and rc4 images were retained for rollback. This is a historical checkpoint, not a live health feed. The earlier four-instance shutdown record predates this release; no end-of-day AWS shutdown or mirror-session inventory was verified on 24 November.

## Architecture

```text
EC2 Worker --[original TCP connection]----------------------> EC2 Control Plane
     |
     +--[temporary Traffic Mirroring: VXLAN/UDP 4789]--> Zeek
                                                         |
                                        conn.log / archived JSONL.gz
                                                         |
                                         collector (systemd, SSH)
                                                         |
                              Control Plane: restricted SSH receiver
                                                         |
                                  private store + ingestion receipt
                                                         |
                                    publisher + success heartbeat
                                                         |
                                     read-only published snapshot
                                                         |
                              k3s hostPath /app/data/zeek (read-only)
                                                         |
                           BlueGuard FastAPI + static UI (one Pod)
                        snapshot / publisher / ingestion / quality APIs
                                                         |
                              private ClusterIP Service :80
                                                         |
                                    SSH-tunneled browser
```

The backend and static frontend run in the **same container and Pod**. Zeek, collector and publisher are host services, not Kubernetes Pods. Telemetry is acquired periodically, not streamed live.

## Latest release and observed telemetry

| Check | Observed result |
|---|---|
| Application QA | 54/54 passed (37 existing, 14 Quality Gate backend, 3 UI smoke tests) |
| Container file checks | 24/24 SHA-256 matches against the rc4 development tree |
| Image smoke test | UID 10001, version rc4, six required GET routes in OpenAPI |
| Canary and promotion | Rollouts completed; main Service excluded Canary before promotion; seven HTTP endpoints succeeded |
| Final state | Main rc4 Deployment 1/1 Ready; zero restarts; Canary deleted |
| Quality Gate at 18:40:40 UTC | `degraded`; snapshot `stale`; publisher `healthy`; ingestion `stale`; `gaps_observed` |
| Available snapshot | 11 records; 9,136,929 aggregate `missed_bytes`; complete field coverage |

`degraded` is the expected classification of the available snapshot, not a failed deployment. Old gaps do not prove an ongoing capture incident. Zero gaps, likewise, would not prove lossless capture. The seven alert examples remain synthetic; the Zeek connection records are separate periodic telemetry. The [release report](docs/telemetry-quality.md) and [structured evidence](evidence/2026-11-24/result.json) document the policy and validation limits.

## Measured network results

| Experiment | Controlled workload | Measured network observation |
|---|---|---|
| HTTP mirroring, 16 Nov | Three HTTP GET requests | 3/3 HTTP 200; corresponding Zeek records |
| LIVE-AD-03, 18 Nov | 5 MiB, 256 KiB/s | 247 outbound mirror-skipped packets; Zeek `missed_bytes=357160` |
| LIVE-AD-04, 18 Nov | 5 MiB, 64 KiB/s | 3 outbound + 1 inbound mirror-skipped packets; Zeek `missed_bytes=4344` |
| LIVE-AD-05, 19 Nov | 5 MiB, 32 KiB/s | Zeek UID `CQN9op1cWFef1nHdCj`, `missed_bytes=0` |
| Diagnostic review, 24 Nov | Existing 300 s CloudWatch interval | 685,240 inbound mirror bytes, 6,979 outbound mirror bytes, zero skip bytes reported in both directions; no proof of complete capture |

The historical experiments and their caveats remain in [experimental results](docs/experimental-results.md). `missed_bytes=0` applies to an observed connection, not a general guarantee. AWS skip metrics and Zeek reconstruction gaps measure different phenomena.

## Source availability

The repository now contains the recovered **v0.5.0-rc4** application sources,
static assets, regression tests, Control Plane telemetry pipeline, Zeek collector,
sensor configuration and aligned Kubernetes manifests.

The 54 successful tests and container checks reported above are historical
AWS release evidence. Validation of the consolidated Git checkout through
GitHub Actions is pending. A bit-for-bit reproducible build and a fresh
end-to-end deployment have not yet been established.

See [source inventory and remaining requirements](docs/source-availability.md).

## Repository contents

| Location | Contents |
|---|---|
| [`applications/`](applications/) | v0.5.0-rc4 API source, tests and Kubernetes laboratory baseline |
| [`blue-team/zeek/`](blue-team/zeek/) | Recovered Zeek configuration, collector, detection policies and systemd units |
| [`blue-team/wazuh/`](blue-team/wazuh/) | Wazuh integration scope; no deployed integration artifacts |
| [`infrastructure/`](infrastructure/) | AWS templates, Control Plane telemetry pipeline and historical Kubernetes manifests |
| [`scripts/`](scripts/) | AWS/SSH/diagnostic helpers; review before use |
| [`evidence/`](evidence/) | Structured lab observations and selected terminal excerpts |
| [`docs/architecture.md`](docs/architecture.md) | Components, trust boundaries, data flow |
| [`docs/telemetry-quality.md`](docs/telemetry-quality.md) | rc4 API contract, policy, test and release observations |
| [`docs/experimental-results.md`](docs/experimental-results.md) | Experiment measurements and interpretation |
| [`docs/implementation.md`](docs/implementation.md) | Software components and scheduling |
| [`docs/verification.md`](docs/verification.md) | Test matrix and read-only checks |
| [`docs/security.md`](docs/security.md) | Controls and residual risks |
| [`docs/limitations.md`](docs/limitations.md) | Unimplemented capabilities and constraints |
| [`docs/operations.md`](docs/operations.md) | EC2 lifecycle, validation, cleanup and rollback |
| [`docs/roadmap.md`](docs/roadmap.md) | Next release and acceptance criteria |

## Operational constraints

- Private ClusterIP and SSH forwarding only; no public Ingress or application authentication. No NetworkPolicies were present in the `blueguard` namespace at the rc4 review; ClusterIP is not a pod-level security boundary.
- Traffic Mirroring is temporary and billable while provisioned; approved test sessions must be explicitly removed.
- Collector/publisher timers and UI polling are periodic; the Zeek connection view refreshes every 30 s and the Quality Gate every 60 s while visible.
- The bounded store (1 MiB/batch, 10 MiB and 10,000 records total) has no durable retention or high availability.
- Review organizational policy, evidence and network metadata before external publication. Do not commit credentials, raw captures or operational stores.

**Documentation baseline:** 25 November 2026, based on historical repository evidence and supplied terminal outputs. [Changelog](CHANGELOG.md).
