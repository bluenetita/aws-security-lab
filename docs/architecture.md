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
                                         conn-ingested.jsonl (0440)
                                                               |
                                         read-only Kubernetes hostPath
                                                               v
                    blueguard namespace / blueguard-api Deployment (1 replica)
                           1 Pod, 1 container: FastAPI + static frontend
                               /api/v1/zeek/connections :8080
                                             |
                        blueguard-api ClusterIP Service :80
                                             |
                               Local SSH tunnel :18083
                                             |
                                         Web browser
```

The traffic-mirror session must exist for the Zeek instance to observe the selected Worker ENI traffic. The original network connection is not routed through Zeek.

## Kubernetes resources

| Resource | Observed configuration |
|---|---|
| Namespace | `blueguard` |
| Deployment | `blueguard-api`, 1 desired replica |
| Pod | 1 container with FastAPI backend **and static frontend** |
| Service | `blueguard-api`, `ClusterIP` (`10.43.19.117:80` at validation) |
| Container image | `localhost/blueguard-api:0.4.2`; `imagePullPolicy: Never` |
| Placement | `nodeSelector` targeting control-plane hostname |
| Volume | Host `/var/lib/blueguard/zeek` mounted read-only at `/app/data/zeek` |
| Probes | `/healthz` and `/readyz` |
| Identity | nonroot UID/GID 10001, restricted capabilities, read-only root filesystem |

The application is **not a two-Pod frontend/backend architecture**. Kubernetes only runs BlueGuard; Zeek and ingestion processes are Linux host services.

## Trust boundaries

1. **AWS capture:** SG controls UDP/VXLAN traffic into Zeek; mirror scope is defined by the session and filter.
2. **Zeek → Control Plane:** source-bound Ed25519 SSH identity, pinned server host key, forced receiver command, private network transport.
3. **Receiver → application:** private writeable store is separate from a publisher-generated read-only snapshot; Pod has no direct access to receiver files.
4. **Browser → API:** private `ClusterIP` reachable through an operator-controlled SSH tunnel. The application itself has no end-user authorization.

## Availability and data freshness

There is one application replica, local hostPath data and node-local OCI images. The workload is not highly available and does not automatically fail over to another node. Collector and publisher execute approximately once per minute; the frontend refreshes at 30-second intervals when active. These are periodic snapshots, not continuous streaming.
