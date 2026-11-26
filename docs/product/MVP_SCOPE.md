# Product MVP scope and exclusions

Status: **proposed**, 26 November 2026. See [Product Vision](PRODUCT_VISION.md) for the four maturity levels and [Product Requirements](PRODUCT_REQUIREMENTS.md) for numbered requirements.

## Technical Alpha boundary

Technical Alpha is a private **internal** integration milestone. It covers normalized imported Wazuh alerts, the first Data Exfiltration candidate pack, source-specific Assurance, and regression-preserved rc4 monitoring. Its read-only published snapshot may remain bounded and host-local. Unauthenticated access is limited to authorized internal test environments and approved test data; it never permits customer access. This scope does not imply that Wazuh integration, rules, or Zeek policies have been validated in the current checkout.

## Product MVP release scope

Product MVP inherits the validated Technical Alpha capabilities and becomes a private **single-tenant customer pilot** only after the following additional capabilities are implemented and validated:

- Authentication, server-side RBAC, and auditable investigation state changes.
- Secure collector identity, credential storage and rotation, and least-privilege Wazuh access.
- Persistent storage, documented retention, tested backup/restore, and a reproducible installation and rollback procedure.
- Wazuh endpoint inventory, bounded alert investigation workflow, operational notifications and reporting.
- An expected source registry and retained, queryable history of time-windowed telemetry assurance anomalies, with security alerts and telemetry operational incidents kept distinct.
- Independent application availability and error monitoring.
- A security review and explicit customer-access readiness decision, including network controls and handling of sensitive security metadata.

The release gate must include tests for unauthorized access, loss/replay of collector data, stale feeds, restore integrity, failure recovery, and preservation of rc4 contracts. Record the tested commit, environment, Wazuh version, reviewer, and residual limitations. Detection candidates retain their uncertainty; pilot approval does not establish complete capture or proven detection efficacy.

## Excluded from the initial Product MVP

Public exposure, shared multi-tenancy, billing, automated active response, broad SIEM search and correlation, and a commercial release claim are excluded. Additional detection packs and automated AWS collection remain separately prioritized work. Historical laboratory addresses, thresholds, full Wazuh Manager configuration, and reference response scripts are not product defaults.

Licensing, contributor ownership, and third-party provenance must be resolved before importing reference code or commercially distributing a combined product. Product MVP planning does not grant those rights.
