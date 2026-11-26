# Architecture decisions

| Decision | Rationale | Consequence / limit |
|---|---|---|
| k3s on EC2 | Study and operate Kubernetes components directly in a bounded lab | Kubernetes control plane remains self-managed |
| Zeek outside Kubernetes | Decouple packet observation from application scheduling | Dedicated EC2 sensor and network rules required |
| AWS Traffic Mirroring | Observe Worker traffic without installing Zeek on the Worker | Additional billing; incomplete mirrors possible |
| Restricted SSH ingestion | Authenticated encrypted transfer without a public ingestion API | Key management and host-specific SSH configuration required |
| Dedicated receiver and publisher | Keep a private write store out of the unprivileged Pod | Adds timer latency and an additional operating component |
| JSONL snapshots | Simple interoperable prototype for low-volume tests | Bounded storage; no indexing, retention or HA |
| One Pod for API + static UI | Minimal dependencies and resource use for the prototype | Frontend/backend cannot be scaled independently |
| Node-local OCI image + `hostPath` | Fast iteration with no registry or database | Single-node dependency; not portable/high availability |
| ClusterIP + SSH tunnel | Avoid public application exposure while auth is absent | Not a customer access solution |
| Composed quality policy v1 | Reuse existing health models and preserve gap evidence/reasons | Snapshot-wide assessment; no atomic joint read; no automatic alert suppression |
| Parallel Canary with separate selector | Validate release against shared read-only telemetry before promotion | No traffic splitting; no complete network isolation without NetworkPolicies |
| Incremental offline rc4 build | Freeze rc3 runtime dependencies during QA | Not a reproducible clean build; synchronize source and pin dependencies for stable release |
| Separate CloudWatch collector (planned) | Keep AWS credentials/permissions outside API and preserve on-prem portability | rc5 design only; IAM and data contract still require validation |

All decisions are scoped to the laboratory version; production design requires a separate architecture/security review.

## M3.3 collector checkpoint continuity decision

**Status:** committed at `906a865` after scoped independent review; no new
deployment verified. This laboratory decision does not approve any proposed
product ADR below.

The active-file checkpoint keeps its top-level state version and adds a
SHA-256 anchor for up to 4096 bytes before the exact byte offset. The
collector uses descriptor-based positional reads to bypass Python buffering,
checks the last persisted anchor and a full digest of each pending batch
before delivery and after ACK, and advances state only after successful
validation and atomic persistence. The restricted SSH path and archive
checkpoint behavior remain unchanged.

The alternatives considered were trusting device/inode/size alone (shown to
skip records after truncation/refill), trusting buffered seek/read (shown to
return stale bytes), and replaying the active file on every run (unnecessary
duplicate traffic and capacity pressure). The bounded anchor plus full
pending-batch checks reduce observable skips without adding a dependency or
changing transport. They add local reads and cannot detect every concurrent
rewrite. Legacy nonzero active checkpoints replay from zero; malformed state
fails explicitly. Replayed ACKed records rely on receiver deduplication and
may encounter its storage limit.

Rollback to the older collector would ignore continuity metadata and restore
the silent-skip risk. An operator must review the checkpoint and arrange a
safe active-file replay/reset and receiver capacity before any rollback;
neither state editing nor live rollback was performed during M3.3.

## M3.4 adaptive profile lifecycle decision

**Status:** approved local policy correction and scoped source review;
uncommitted at this documentation update. This laboratory decision does not
approve any proposed product ADR below.

BG-BUG-003 showed that saturated Adaptive host and destination profile tables
could keep new identities at `capacity_exceeded` after long inactivity. The
policy now records the last real active-window callback for each existing
profile and expires host and destination entries independently when completed
window network time reaches a configurable inactivity interval (60 minutes by
default). The tick barrier runs after real callbacks and before delayed
baseline confirmation. Pending samples are discarded with structured audit;
the separate expiration record reports retired confirmed history. Source-wide
learning holds remain independent. Invalid nonpositive intervals warn and
disable expiry while preserving capacity limits.

Admission-time eviction was rejected because an existing identity might still
receive a callback later in that tick. LRU eviction could discard active
baselines, and persistent storage or a separate activity table would add
complexity and resource bounds to review. The barrier approach can leave a new
identity blocked until a later callback. The default TTL is not production
calibrated; shorter retention resets useful learning, while longer retention
prolongs saturation. Synthetic tests do not prove capture completeness or
real-world detection efficacy. See [verification](verification.md).

## Proposed product ADRs — not approved

The following are decision records to write and review before the corresponding implementation. They do not supersede the historical laboratory decisions above. Each ADR should record the selected option, alternatives, tradeoffs, security impact, evidence, owner, and reversal path. The maturity gates are in [Product Roadmap](product/PRODUCT_ROADMAP.md).

| ID | Proposed decision | Alternatives and open tradeoff | Needed by |
| --- | --- | --- | --- |
| P-01 | Keep FastAPI as a modular monolith with external collectors and independent Zeek/Wazuh engines. | Separate product services or direct vendor polling from FastAPI; weigh operational complexity and credential isolation. | M4 |
| P-02 | Version imported-alert contracts and keep rc4 synthetic and replayed-fixture provenance distinct. | Extend existing synthetic routes or provide new routes; assess compatibility and risk of misleading data. | M4 |
| P-03 | Select Wazuh Indexer API for initial alert acquisition, if version/schema/permissions validate; assess Server API separately for agent/manager health. | Other export surfaces; compare stable IDs, pagination, authorization, and operational support. | M4 |
| P-04 | Define cursor persistence, bounded replay, deduplication, atomic publication, failure state, and retention for the Technical Alpha. | Existing bounded snapshot versus a new store; compare recovery and consistency. | M4 |
| P-05 | Version source-specific Assurance without changing Quality Gate policy v1 semantics. | Independent source assessments versus combined policy; assess false assurance and migration. | Initial source-state semantics by M4; expanded Assurance design by M7. |
| P-06 | Define source identity and correlation uncertainty across Zeek and Wazuh. | IP-only, agent ID, and time-window joins; account for NAT, reuse, clock skew, and missing identity. | Source identity by M4; correlation semantics by M6. |
| P-07 | Define Product MVP authentication, server-side RBAC, audit, customer access, and network controls. | Identity provider and deployment choices; `ClusterIP` alone is not isolation. | Preliminary threat model and access requirements before live M5; customer-facing controls by M8. |
| P-08 | Select persistent storage and retention/backup/recovery design. | PostgreSQL is a candidate, not an approved dependency; compare operational burden and recovery needs. | Initial retention and recovery requirements before live M5; persistent storage design by M8. |
| P-09 | Decide licensing, ownership, third-party provenance, attribution, and allowed reference-code reuse. | Independent implementation versus reviewed import; obtain legal/product decision before affected use. | Before reference-code reuse, affected Detection Pack implementation, or third-party deployment/distribution. |
