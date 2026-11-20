# Known limitations and work remaining

| Priority | Area | Current limitation | Required work |
|---|---|---|---|
| High | Reproducibility | This archive contains application source v0.2.0, but deployment evidence refers to v0.4.2 | Export, review and version the real v0.4.2 source/manifest and host ingestion units |
| High | Ingestion capacity | Receiver limited to 1 MiB per batch and 10 MiB/10,000 stored records | Durable storage, retention and saturation alerts |
| High | Detection | Seven demo alerts are synthetic; no Zeek/Wazuh detection pipeline is integrated | Detection rules, enrichment and correlation with test evidence |
| High | App security | No end-user authentication, authorization or tenant isolation | Identity, RBAC, tenant-aware data layer, audit trail |
| High | Full E2E proof | New mirrored connection after v0.4.2 release not tracked all the way to UI | Timed test with fresh Zeek UID and cleanup of mirror session |
| Medium | Availability | One Pod, local image and `hostPath` on Control Plane | Registry, persistent storage, failover, recovery testing |
| Medium | Freshness | Collector + publisher periodic timers; frontend polling | End-to-end lag metrics, explicit stale-sensor indication |
| Medium | Packet observation | Previous mirroring tests had missing packets; 05 was one loss-free Zeek connection | Repeated measurements under load and full CloudWatch metrics |
| Medium | API semantics | Legacy flags can imply no Zeek connectivity despite successful file ingestion | Version API status and distinguish sensor/transport/storage health |
| Medium | Operations | Cloud costs continue for running EC2 and traffic-mirror sessions | Environment inventory, budget alerts, automated/approved cleanup |

No claim of production readiness, guaranteed delivery, zero packet loss, attack detection or customer isolation is justified by the recorded results.
