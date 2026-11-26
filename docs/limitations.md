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
| Medium | Build/CI | Historical run #3 passed on `caa8ce1` per the project owner. Run #7 passed on `a2fee23` with verified step conclusions, but detailed logs returned HTTP 403 and actual CI test counts remain unverified. The original incremental image inherits rc3 dependencies; the `httpx`/`TestClient` `StarletteDeprecationWarning` remains. | Pin base digest and transitive dependencies, resolve the warning, and assess image scanning/provenance |
| Medium | Recovered host components | The M3.3 host pipeline has 41 passing local synthetic regression tests and owner-reported independent collector review; live service behavior and a fresh full-path trace remain unverified | Separately authorized host/full-path verification with recorded results |
| Medium | Zeek policy validation | The M3.4 Zeek 9.0.1 suite passes 59 local offline tests, including BG-BUG-003 recovery and native JSON schema checks, but is not in CI. Synthetic tests do not prove detection efficacy or complete capture. Default-limit profile memory and performance are unmeasured. | Integrate an approved CI runtime and measure resource behavior with controlled data no later than M6 Detection Pack acceptance |
| Medium | Adaptive baseline retention | A 60-minute laboratory inactivity interval can discard useful history or keep capacity blocked; a newly blocked identity can enter only on a later callback after the expiration barrier. Capture gaps or absent finalized connections can make observed inactivity misleading. | Calibrate TTL, limits and response under representative capture and load before operational claims |
| Medium | Operations | Running EC2 and mirror sessions can incur charges; shutdown verified on 25 November | Inventory, budget alerts and approved cleanup |

## M3 readiness disposition and release gates

The M3 decision is **CONDITIONAL GO for offline M4 Wazuh Alert Contract work**.
The table above retains technical debt; the gate map below states when each
remaining risk must be resolved or explicitly accepted. Offline contract
design uses local source, synthetic fixtures and no live service, so the
absence of a fresh AWS trace does not block that narrow work.

| Risk or missing capability and evidence | Blocks offline M4? | Proposed milestone or release gate |
| --- | --- | --- |
| Zeek tests passed 59/59 locally but are absent from CI; run #7 cannot validate detector behavior. CI logs returned HTTP 403, so actual CI test counts remain unverified. | No | Integrate reproducible Zeek policy regression execution and inspect attributable results no later than M6 Detection Pack acceptance. |
| Adaptive limits have focused saturation tests but no default-limit memory or performance measurements; the 60-minute TTL and detector thresholds are laboratory settings. | No | Measure and calibrate limits, TTL and thresholds under controlled representative load by M6 Detection Pack acceptance; retain candidate/uncertainty language until then. |
| Historical Traffic Mirroring gaps and missing packets show that capture completeness is unproven. Offline PCAP and event tests do not measure live coverage. | No | Quantify mirror scope and loss before live M5 acceptance; carry quality uncertainty into M6 detection claims. Never infer universal completeness from one trace. |
| No fresh timed rc4 event-to-browser or corrected collector/Adaptive live trace exists; M3 changes have not been deployed to AWS. | No | Require separately authorized controlled end-to-end evidence before claiming live M5 integration or M6 detector effectiveness. |
| Receiver storage and batches are bounded; collector ACK/replay can duplicate records and continuity evidence covers only a 4096-byte prior anchor. Local 41/41 tests do not establish exactly-once delivery. | No | Specify bounds, cursor, replay, retention and explicit failure states in M4; exercise live failure/recovery and saturation before M5 acceptance; durable retention by M8. |
| Reproducible provisioning, base digest, transitive dependency pinning and bit-for-bit image reproduction remain unverified despite successful CI builds; the `httpx`/`TestClient` deprecation warning remains. | No | Use a reviewed, approved environment for live M5; require reproducible installation, dependency provenance, warning resolution and rollback by M8 Product MVP gate. |
| API lacks end-user authentication, authorization and security-action auditing; historical `ClusterIP` access does not provide pod isolation. | No, for offline design with synthetic data | Define preliminary threat model and internal-access requirements before live M5; implement and test auth, server-side RBAC, audit and customer network controls by M8, before any pilot. |
| Ownership, licensing and third-party provenance for reference material remain undecided; no import is authorized by M3. | No, if M4 uses independently authored fixtures and contracts | Resolve before any reference-code reuse or affected M6 pack implementation, and before M9 third-party distribution. |
| Product ADRs P-01 through P-09 remain proposed. M4 source/API, provenance, identity, state and replay choices are open decisions. | No; deciding them is M4 work | Review and approve affected contract decisions during M4 before implementation; preliminary access/retention decisions before live M5; remaining Product MVP decisions by M8. |
| Wazuh alert ingestion is not implemented; the seven rc4 demo alerts are synthetic. Historical application QA reported 54 tests, while run #7 confirmed its application step without accessible counts. | No | Define the imported-alert contract and preserve rc4 routes in M4; validate a least-privilege live feed in M5 and candidate detection context in M6. |
| One Pod and host-local images/storage provide no HA; Quality Gate observations are snapshot-wide and not atomic; independent AWS/source health collection is absent. | No | Define source-specific states in M4; validate independent source Assurance by M7; address storage, HA, recovery and application monitoring by M8. |
| UI checks are HTTP/static smoke tests, not full browser interaction; operational cost and cleanup evidence are historical. | No | Add internal workflow/browser evidence by M7; require approved inventory, budget and cleanup controls before live M5 operations. |

Live integration is **not ready** without the M4 contract, a selected Wazuh
version/API and least-privilege credentials, approved environment, threat and
retention requirements, and controlled failure and end-to-end evidence.
Production deployment is **not ready** without the M8 security, persistence,
reproducibility and customer-access gates, plus applicable legal approval.

No claim of production readiness, guaranteed delivery, zero packet loss, attack detection or customer isolation is justified by the recorded results.
