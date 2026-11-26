# System architecture

## Deployment topology

**Environment:** AWS region `eu-south-1`, private lab subnet `10.20.1.0/24`, k3s on two EC2 instances.

| Host role | Private address | Components |
|---|---|---|
| Control Plane | `10.20.1.10` | k3s server, SSH receiver, ingestion store, publisher, BlueGuard Pod |
| Worker | `10.20.1.11` | k3s agent, HTTP traffic source for experiments |
| Zeek Sensor | `10.20.1.9` | Zeek traffic analyzer, collector and collector timer |
| Wazuh | `10.20.1.16` | EC2 resource only; application integration not verified |

IP addresses above are **historical private lab addresses**, not endpoint discovery or a deployment template. Validate current network configuration before operational use.

## Network-data path

```text
Worker (source ENI) ---------------- TCP/18080 ----------------> Control Plane
    |
    +---- VPC Traffic Mirroring session, VXLAN UDP/4789 -----> Zeek
                                                               |
                                                 conn.log + rotated .gz
                                                               |
                                         collector (incremental, systemd)
                                                               |
                                           restricted SSH TCP/22 / ACK
                                                               v
                                           receiver (forced command)
                                                               |
                                      /var/lib/blueguard-ingest/incoming/
                                                 conn.jsonl (0600)
                                                               |
                                       publisher (systemd, minutely)
                                                               v
                                        /var/lib/blueguard/zeek/
                        conn-ingested.jsonl (0440) + publisher/ingestion health JSON
                                                               |
                                         read-only Kubernetes hostPath
                                                               v
                    blueguard namespace / blueguard-api Deployment (1 replica)
                           1 Pod, 1 container: FastAPI + static frontend
                       /api/v1/zeek/connections + telemetry health/quality :8080
                                             |
                        blueguard-api ClusterIP Service :80
                                             |
                               Local SSH tunnel :18083
                                             |
                                         Web browser
```

The traffic-mirror session must exist for the Zeek instance to observe the selected Worker ENI traffic. The original network connection is not routed through Zeek.

## Collector continuity (M3.3 local source)

The pending M3.3 collector source extends the version-1 active checkpoint with
`continuity: {offset, window_bytes, sha256}`. The digest covers up to 4096
bytes immediately before the committed offset; device and inode checks and
archive line checkpoints remain. On an existing nonzero active checkpoint
without continuity evidence, the collector replays the active file from byte
zero. Archive checkpoints are preserved. A changed active fingerprint also
causes replay from zero, while malformed checkpoint metadata is rejected.

For each pending batch, the collector hashes all bytes it read, including
blank lines, and retains the preceding committed anchor separately. Fresh
`os.pread` calls on the opened descriptor verify the anchor and pending batch
before delivery and after a receiver ACK, before atomic checkpoint
persistence. Short reads or observable rewrites abort with a diagnostic that
does not include event content. Only opening a missing active log is benign;
transport and persistence `FileNotFoundError` failures propagate. An ACK
followed by a failed check or save can cause replay; the receiver remains the
deduplication authority. Normal file append does not invalidate the already
read prefix. This is a locally tested source change, not evidence of a new
deployment or guaranteed delivery. See [decision record](decisions.md) and
[verification](verification.md).

## Kubernetes resources

| Resource | Observed configuration |
|---|---|
| Namespace | `blueguard` |
| Deployment | `blueguard-api`, 1 desired replica |
| Pod | 1 container with FastAPI backend **and static frontend** |
| Service | `blueguard-api`, `ClusterIP` (`10.43.19.117:80` at validation) |
| Container image | `localhost/blueguard-api:0.5.0-rc4`; `imagePullPolicy: Never` |
| Placement | `nodeSelector` targeting control-plane hostname |
| Volume | Host `/var/lib/blueguard/zeek` mounted read-only at `/app/data/zeek` |
| Probes | `/healthz` and `/readyz` |
| Identity | nonroot UID/GID 10001, restricted capabilities, read-only root filesystem |

The application is **not a two-Pod frontend/backend architecture**. Kubernetes only runs BlueGuard; Zeek and ingestion processes are Linux host services.

## Trust boundaries

1. **AWS capture:** SG controls UDP/VXLAN traffic into Zeek; mirror scope is defined by the session and filter.
2. **Zeek → Control Plane:** source-bound Ed25519 SSH identity, pinned server host key, forced receiver command, private network transport.
3. **Receiver → application:** private writeable store is separate from a publisher-generated read-only snapshot; Pod has no direct access to receiver files.
4. **Browser → API:** private `ClusterIP` reachable through an operator-controlled SSH tunnel. The application itself has no end-user authorization; no NetworkPolicies were present in the namespace at review.

## Availability and data freshness

There is one application replica, local hostPath data and node-local OCI images. The workload is not highly available and does not automatically fail over to another node. Collector and publisher execute approximately once per minute; the Zeek connection view refreshes at 30-second intervals and the Quality Gate at 60-second intervals when active. These are periodic snapshots, not continuous streaming.

## Telemetry quality layer (rc4)

The API reads the same published directory for the connection snapshot, publisher heartbeat and ingestion receipt. The Quality Gate calls the three existing health functions in-process, evaluates their results with policy v1 and returns the original component assessments and reason codes. The frontend displays the result without recalculating the policy. The application does not perform direct AWS queries or probe Zeek connectivity. See [Telemetry Quality Gate](telemetry-quality.md).

During release validation a separate `blueguard-api-canary` Deployment used `app=blueguard-api-canary`, the same control-plane placement and a read-only shared snapshot. The primary Service continued selecting only `app=blueguard-api`. The Canary used loopback port-forwarding and an SSH tunnel, not a public Service, and was deleted after successful promotion. This is selector separation, not complete network isolation.
