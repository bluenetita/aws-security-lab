# BlueGuard product requirements

Status: **proposed**, 26 November 2026. Requirements describe future release gates, not implemented rc4 behavior. The maturity levels and exclusions are defined in [Product Vision](PRODUCT_VISION.md) and [MVP Scope](MVP_SCOPE.md).

## Functional requirements

| ID | Target | Requirement and testable outcome |
| --- | --- | --- |
| F-01 | Alpha | Preserve existing rc4 routes, response fields, synthetic alert semantics, health endpoints, and Telemetry Quality Gate policy v1/reason codes. Contract regression tests must pass before adding a feed. |
| F-02 | Alpha | Provide a separate, versioned read-only imported-alert API and UI view. Imported, synthetic, and replayed fixture events must have distinct provenance; replayed fixtures cannot appear as live imported alerts. |
| F-03 | Alpha | Acquire Wazuh alerts through an external collector. The Indexer API is the preferred candidate, subject to version, schema, permission, pagination, and operations validation. FastAPI must not hold vendor credentials or poll Wazuh. |
| F-04 | Alpha | Validate, bound, deduplicate, and publish complete alert generations. Support bounded replay from a persisted cursor and explicit malformed-input, authorization, transport, stale, and missing-data states. |
| F-05 | Alpha | Present a Data Exfiltration **candidate** pack with source event, rule, and context. Positive, benign, duplicate, late, out-of-order, missing-telemetry, and false-correlation cases must be tested. |
| F-06 | Alpha | Report Wazuh feed freshness and processing separately from Zeek capture and publisher quality. A successful zero-result alert query does not establish source health or telemetry completeness. |
| F-07 | MVP | Authenticate users and enforce server-side RBAC on every protected API and UI operation; record security-relevant actions in audit logs. A private network path alone does not satisfy this requirement. |
| F-08 | MVP | Provide Wazuh endpoint inventory and state, an alert investigation workflow with attributable status changes, operational notifications, and bounded reporting. Define ownership and authorization for each write operation. |
| F-09 | MVP | Use persistent storage with documented retention, backup and restore, and reproducible installation and rollback. PostgreSQL is a candidate, not an approved dependency. |
| F-10 | MVP | Monitor the application independently of the telemetry it assesses, including availability, errors, and resource limits. Pass a security review and customer-access readiness gate before an approved pilot. |
| F-11 | Alpha | Page imported alerts within documented bounds; filter by time, source, severity, and rule; order deterministically with a stable tie-breaker. Test page boundaries and equal timestamps. |
| F-12 | Alpha | Report acquisition outcome, published-generation freshness, and independently observed source health as distinct assessments. A successful empty query cannot make the other assessments healthy. |
| F-13 | Alpha | Give each integrated source a stable identity and record which source and scope each alert and health observation describes. Treat absent or ambiguous identity as unknown. |
| F-14 | Alpha | Where the source supports it, collect an independent availability or heartbeat observation; otherwise report that observation as unknown rather than inferring it from alert count. |
| F-15 | Alpha | Assess Assurance per source and defined time window, with the observation window and evidence gaps visible; preserve Quality Gate policy v1 separately. |
| F-16 | MVP | Maintain an expected source registry with approved source identity, owner, expected reporting behavior, and lifecycle state. Compare expected sources with observed sources without treating silence as zero risk. |
| F-17 | MVP | Retain and query historical telemetry anomalies with source, time window, reason, and resolution context under the documented retention policy. |
| F-18 | MVP | Distinguish security alerts from telemetry operational incidents in API, workflow, notifications, and reporting. An outage must not be relabeled as a security detection. |

## Proposed data contracts

**New alert envelope v1:** schema version; stable BlueGuard ID; source system and instance; original event ID and rule ID; event time, source ingestion time when available, acquisition time, and publication time in UTC; original severity and separately normalized severity; confidence or candidate classification; source identity (agent ID and/or sensor ID); optional network endpoints; bounded human-readable summary; provenance (`imported`, `synthetic`, or `replayed_fixture`); and a source reference. Imported-feed responses accept only `imported` events; test/replay responses identify fixtures explicitly. The existing rc4 synthetic `Alert` contract remains unchanged. Unknown values remain absent or explicitly unknown. Telemetry quality is a separate assessment linked by source and time, never folded into severity or confidence.

**Feed state v1:** source instance, query scope, last attempt and success, cursor/watermark, publication generation, accepted/rejected/duplicate counts, and typed state (`available`, `stale`, `no_data`, `authorization_error`, `transport_error`, `invalid_data`, or `unknown`). `no_data` means the query succeeded with no matching events; it does not prove coverage or health.

**Replay and publication:** deduplication uses source instance plus a stable source event ID, with a documented fallback only if the chosen API lacks one. A time watermark must have a stable tie-breaker and bounded overlap for late events. Cursor persistence and durable publication must be crash-consistent: after a crash, recovery may replay a bounded overlap but must not advance past unpublished events. Readers see one complete generation; on failure, retain the last valid generation and mark its age and failure. Retention or capacity limits must produce an explicit gap/error state and operator-visible evidence, never silent loss. Exact size, page, replay, and retention limits are M4 decisions, verified by boundary and crash-recovery tests.

**Assurance evidence:** keep acquisition outcome, publication freshness, and independent source-health observations separate. Per-source, time-windowed assessments cite their observed interval and limitations. An expected-source registry and historical anomaly record are Product MVP contracts, not requirements for the first narrow Wazuh alert collector.

## Non-functional and security requirements

| ID | Target | Requirement and verification |
| --- | --- | --- |
| N-01 | Alpha | Keep the unauthenticated service private behind operator-controlled access. Preserve non-root execution, read-only root filesystem and telemetry mount, dropped capabilities, no privilege escalation, `RuntimeDefault` seccomp, and disabled service-account token automount. Review rendered manifests. |
| N-02 | Alpha | Keep Zeek's source-bound restricted SSH path and private-store/read-only-publication separation. Give a Wazuh collector its own least-privilege read identity, protected transport, and secret lifecycle. Test denial and rotation procedures before live use. |
| N-03 | Alpha | Bound event size, batch, page, query time, replay window, and store capacity. Reject over-limit input without partial publication; measure capacity against an approved workload before setting operational targets. |
| N-04 | Alpha | Preserve original severity independently of normalized severity, confidence, and quality. Degraded telemetry must not automatically suppress alerts or reduce severity. Test contradictory and missing inputs. |
| N-05 | Alpha | Log failures and counts without credentials, unrestricted raw payloads, packet captures, or unnecessary personal/network metadata. Review fixtures and evidence before sharing. |
| N-06 | MVP | Define and test retention, recovery objectives, restore integrity, audit retention, user/session controls, secure collector identity, and independent application monitoring. Values require product and security approval. |
| N-07 | MVP | Reproduce installation and rollback from documented inputs in an authorized environment. Complete threat review, access testing, dependency/provenance review, and customer-access approval. |
| N-08 | Alpha | Test crash points before and after generation publication and cursor persistence, bounded replay, and retention/capacity exhaustion. No acknowledged source event may disappear silently. |

## Domain and trust boundaries

The FastAPI application remains a modular monolith for presentation and query contracts. Zeek and Wazuh remain independent security engines. Host or service collectors own external acquisition; a publisher owns validated read-only data made available to the application. A bounded snapshot may serve the Technical Alpha; persistent storage is required for Product MVP.

1. **Capture to Zeek:** mirror scope, packet loss, and sensor visibility limit coverage claims.
2. **Zeek to receiver:** retain pinned server identity, source-bound SSH authorization, forced command, bounded input, and private writes.
3. **Wazuh to collector:** validate Indexer API read scope and transport; evaluate the Server API separately for agent/manager health. Neither interface is approved yet.
4. **Private store to application:** publish a consistent read-only generation; the API has no write path into collector stores.
5. **Browser to API:** Technical Alpha access remains limited to authorized internal test environments and approved test data; it has no customer access. Product MVP adds authentication, server-side RBAC, audit, and a reviewed customer-access path. `ClusterIP` alone is not pod-level isolation.

Source-IP-only correlation is insufficient when IPs are reused or translated. Correlation must identify ambiguous joins and clock skew instead of inventing endpoint certainty.
