# Known limitations and work remaining

| Priority | Area | Current limitation | Required work |
|---|---|---|---|
| High | Reproducibility | Repository source is v0.4.2-lab; deployed rc4 source, effective manifest and host ingestion code are not fully bundled | Export, review and synchronize actual rc4 sources, tests, units, manifests and CI |
| High | Ingestion capacity | Receiver limited to 1 MiB per batch and 10 MiB/10,000 stored records | Durable storage, retention and saturation alerts |
| High | Detection | Seven demo alerts are synthetic; no Zeek/Wazuh detection pipeline integrated | Detection rules, enrichment and correlation with test evidence |
| High | App security | No end-user authentication, authorization, tenant isolation or namespace NetworkPolicies | Identity, RBAC, network segmentation, audit trail |
| High | Full E2E proof | Stored telemetry and recent accepted batch verified; no timed fresh UID trace to browser retained for rc4 | Controlled trace with cleanup of test session |
| Medium | Availability | One Pod, node-local images and `hostPath` on Control Plane | Registry, persistent storage, failover, recovery testing |
| Medium | Quality policy | Snapshot-wide gap aggregation; stale historical gaps; component reads not atomic; unknown sensor connectivity | Windowed/connection-level assessments, stronger consistency and independent sensor health |
| Medium | AWS observability | Manual CloudWatch measurements only; no automated AWS collector | rc5; explicit no-data, partial-data, no-session and error states |
| Medium | Packet observation | Missing mirrored packets and gaps have been observed; one zero-gap connection is not universal proof | Further controlled tests as needed, not an assumption of complete capture |
| Medium | UI QA | Three rc4 UI smoke tests serve assets and verify HTML/headers; no automated browser test suite; manual refresh not independently confirmed in retained outputs | Functional browser tests incl. refresh, error and timeout paths |
| Medium | Build/CI | Incremental image inherits rc3 dependencies; workflow in repository still targets v0.4.2 | Pin base digest and transitive dependencies, synchronize CI, scan/sign images |
| Medium | Operations | Running EC2 and mirror sessions can incur charges; shutdown not verified on 24 November | Inventory, budget alerts and approved cleanup |

No claim of production readiness, guaranteed delivery, zero packet loss, attack detection or customer isolation is justified by the recorded results.
