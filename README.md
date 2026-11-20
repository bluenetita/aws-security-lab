# BlueGuard — AWS Network Security Monitoring Lab

BlueGuard is an experimental network-telemetry platform built on **Amazon EC2, k3s Kubernetes and Zeek**. It demonstrates packet mirroring, secure incremental ingestion of Zeek connection records and HTTP-based visualization in a containerized dashboard.

**Scope:** controlled cybersecurity laboratory. The available evidence does **not** establish a production SIEM, an intrusion-detection engine, a managed SOC service or a customer-ready application.

## Implementation status

| Component | Verified implementation | Status |
|---|---|---|
| AWS networking | Private VPC/subnet, EC2 nodes, Security Groups and temporary Traffic Mirroring | Validated in controlled tests |
| Kubernetes | k3s cluster; `blueguard` namespace, one API Deployment/Pod and one private ClusterIP Service | BlueGuard **v0.4.2-lab deployed and healthy** at last check |
| Zeek | VXLAN traffic observation; JSON connection logs; compressed log archives | Verified |
| Ingestion | Incremental collector, restricted SSH receiver, deduplication, checkpoint and retry | Verified with targeted tests |
| Publishing | `systemd` publisher, validated JSONL snapshot, atomic replacement, read-only volume mount | Verified |
| Web application | FastAPI endpoints, Zeek connection view, periodic dashboard refresh | API and UI tested |
| Wazuh | Dedicated EC2 instance; no validated BlueGuard integration | **Not integrated** |

The last observed EC2 shutdown check reported **four stopped instances** and **zero Traffic Mirroring sessions**. These are historical observations, not a live infrastructure-status feed.

## Architecture

```text
EC2 Worker --[normal TCP connection]------------------------> EC2 Control Plane
     |                                                              ^
     +--[temporary AWS Traffic Mirroring; VXLAN/UDP 4789]--> Zeek    |
                                                               |    |
                        Zeek conn.log / archived JSONL.gz      |    |
                                                               v    |
                             Collector (systemd, checkpoint, SSH) --+
                                                                    |
                                   SSH forced-command receiver      |
                                                                    v
                                       Private JSONL ingestion store
                                                                    |
                                   Publisher (systemd, every minute)
                                                                    |
                                    Read-only published JSONL file
                                                                    |
                                          k3s hostPath volume
                                                                    v
                                    BlueGuard FastAPI + static UI
                                      1 Deployment / 1 Pod
                                       ClusterIP Service
                                              |
                                      SSH-tunneled browser
```

The backend and the static HTML/CSS/JavaScript frontend run **in the same container and Pod**. Zeek, the collector and the publisher are **host services, not Kubernetes Pods**.

## Measured results

| Experiment | Controlled workload | Measured network observation |
|---|---|---|
| HTTP mirroring, 16 Nov | Three HTTP GET requests | 3/3 HTTP 200; corresponding Zeek records |
| LIVE-AD-03, 18 Nov | 5 MiB, 256 KiB/s | 247 outbound mirror-skipped packets; Zeek `missed_bytes=357160` |
| LIVE-AD-04, 18 Nov | 5 MiB, 64 KiB/s | 3 outbound + 1 inbound mirror-skipped packets; Zeek `missed_bytes=4344` |
| LIVE-AD-05, 19 Nov | 5 MiB, 32 KiB/s | Zeek UID `CQN9op1cWFef1nHdCj`, `missed_bytes=0` |

`missed_bytes=0` refers to **one observed connection**, not a general guarantee of lossless mirroring. Tests at different rates do not independently establish causality.

Additional results: receiver deduplication (`new=1`, then `duplicates=1`), collector **8/8 unit tests**, successful SSH retry recovery, `systemd` timer runs, and successful v0.4.2 Kubernetes rollout (`1/1 Running`, 0 restarts at check). The API returned **one real Zeek connection**. The **seven dashboard alerts are synthetic**. The included historical v0.2.0 API regression suite also passed **7/7 local tests** during archive verification; these are not tests of the deployed v0.4.2 source.

Detailed data and test limitations: [experimental results](docs/experimental-results.md) · [verification matrix](docs/verification.md).

## Source availability — important

**The included application source is the original `v0.2.0` snapshot**, under [`applications/blueguard-api/`](applications/blueguard-api/). The later **v0.4.2-lab** image and manifest were built and deployed on EC2, but the matching v0.4.2 source files were **not present in the input archive** and are **not included here**.

Accordingly, this repository **documents verified v0.4.2 lab results but does not yet reproduce the v0.4.2 deployment from source**. Do not deploy the older v0.2.0 manifest as a replacement for the running v0.4.2 workload. See [source inventory and synchronization requirements](docs/source-availability.md).

## Repository contents

| Location | Contents |
|---|---|
| [`applications/`](applications/) | Preserved v0.2.0 API source, tests and example Kubernetes manifests |
| [`blue-team/zeek/`](blue-team/zeek/) | Observed Zeek configuration fragments and historical service unit |
| [`blue-team/wazuh/`](blue-team/wazuh/) | Wazuh integration scope; no deployed integration artifacts |
| [`infrastructure/`](infrastructure/) | AWS templates and historical Kubernetes manifests |
| [`scripts/`](scripts/) | AWS/SSH/diagnostic helpers; review before use |
| [`evidence/`](evidence/) | Structured lab test observations and selected terminal excerpts |
| [`docs/architecture.md`](docs/architecture.md) | Components, trust boundaries, data flow |
| [`docs/experimental-results.md`](docs/experimental-results.md) | Experiment measurements and interpretation |
| [`docs/implementation.md`](docs/implementation.md) | Software components and scheduling |
| [`docs/verification.md`](docs/verification.md) | Test matrix and read-only validation commands |
| [`docs/security.md`](docs/security.md) | Implemented controls, residual risks |
| [`docs/limitations.md`](docs/limitations.md) | Unimplemented capabilities and operational constraints |
| [`docs/operations.md`](docs/operations.md) | EC2 lifecycle, observability and safe cleanup |

## Operational constraints

- Access to the dashboard in the laboratory is through a **private Kubernetes Service plus SSH forwarding**. No public Ingress or application authentication is configured.
- Traffic Mirroring is **temporary** and incurs AWS charges while provisioned. Cleanup requires removing the session explicitly.
- `systemd` timers collect/publish periodically. The UI polls every 30 s in the relevant view; this is **not streaming**.
- The current store is bounded (1 MiB/batch; 10 MiB and 10,000 records total) and does **not** implement durable retention or high availability.
- Before external publication, review organization policies, AWS account details, logs and network metadata. No secret material should enter the repository.

**Documentation baseline:** results and release verification from 16–19 November 2026; EC2 shutdown state verified later through AWS CLI outputs. See [CHANGELOG](CHANGELOG.md).
