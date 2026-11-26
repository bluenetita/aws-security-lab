# Known limitations and work remaining

| Priority | Area | Current limitation | Required work |
|---|---|---|---|
| High | Reproducibility | CI built the consolidated rc4 application image at `caa8ce1`; bit-for-bit image reproducibility, reproducible provisioning and fresh end-to-end AWS validation remain unverified | Pin dependencies and base digest; establish reproducible provisioning and test image reproducibility |
| High | Ingestion capacity | Receiver limited to 1 MiB per batch and 10 MiB/10,000 stored records | Durable storage, retention and saturation alerts |
| High | Collector continuity | M3.3 detects tested truncation/refill and multi-batch rewrites, but its persisted anchor covers only the preceding 4096 bytes; changes outside checked ranges or between checks can escape detection. ACKed batches can replay after a failed validation or save. CI run `45812342775` is reported successful on `906a865`, but detailed test counts remain unverified. | Review remaining races, bounded replay/capacity behavior and operator rollback procedure; validate in an authorized host environment |
| High | Detection | Seven demo alerts are synthetic; no Zeek/Wazuh detection pipeline integrated | Detection rules, enrichment and correlation with test evidence |
| High | App security | No end-user authentication, authorization, tenant isolation or namespace NetworkPolicies | Identity, RBAC, network segmentation, audit trail |
| High | Full E2E proof | Stored telemetry and recent accepted batch verified; no timed fresh UID trace to browser retained for rc4 | Controlled trace with cleanup of test session |
| Medium | Availability | One Pod, node-local images and `hostPath` on Control Plane | Registry, persistent storage, failover, recovery testing |
| Medium | Quality policy | Snapshot-wide gap aggregation; stale historical gaps; component reads not atomic; unknown sensor connectivity | Windowed/connection-level assessments, stronger consistency and independent sensor health |
| Medium | AWS observability | Manual CloudWatch measurements only; no automated AWS collector | rc5; explicit no-data, partial-data, no-session and error states |
| Medium | Packet observation | Missing mirrored packets and gaps have been observed; one zero-gap connection is not universal proof | Further controlled tests as needed, not an assumption of complete capture |
| Medium | UI QA | Three rc4 UI smoke tests serve assets and verify HTML/headers; no automated browser test suite; manual refresh not independently confirmed in retained outputs | Functional browser tests incl. refresh, error and timeout paths |
| Medium | Build/CI | BlueGuard CI run #3 passed on `caa8ce1` per the project owner, but the original incremental image inherits rc3 dependencies; the `httpx`/`TestClient` `StarletteDeprecationWarning` remains | Pin base digest and transitive dependencies, resolve the warning, and assess image scanning/provenance |
| Medium | Recovered host components | The M3.3 host pipeline has 41 passing local synthetic regression tests and owner-reported independent collector review; live service behavior and a fresh full-path trace remain unverified | Separately authorized host/full-path verification with recorded results |
| Medium | Zeek policy validation | The M3.4 Zeek 9.0.1 suite passes 59 local offline tests, including BG-BUG-003 recovery and native JSON schema checks, but is not in CI. Synthetic tests do not prove detection efficacy or complete capture. Default-limit profile memory and performance are unmeasured. | Review the staged policy and tests; later integrate an approved CI runtime and measure resource behavior with controlled data |
| Medium | Adaptive baseline retention | A 60-minute laboratory inactivity interval can discard useful history or keep capacity blocked; a newly blocked identity can enter only on a later callback after the expiration barrier. Capture gaps or absent finalized connections can make observed inactivity misleading. | Calibrate TTL, limits and response under representative capture and load before operational claims |
| Medium | Operations | Running EC2 and mirror sessions can incur charges; shutdown verified on 25 November | Inventory, budget alerts and approved cleanup |

No claim of production readiness, guaranteed delivery, zero packet loss, attack detection or customer isolation is justified by the recorded results.
