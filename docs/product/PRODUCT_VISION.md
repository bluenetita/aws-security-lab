# BlueGuard product vision

Status: **proposed**, 26 November 2026. Management approval to proceed with product development is reported by the project owner; this document is not approval of a particular architecture, release, or customer deployment. See [Product Requirements](PRODUCT_REQUIREMENTS.md), [MVP Scope](MVP_SCOPE.md), and the supplied *BlueGuard Technical Asset Assessment* for the underlying source assessment.

## Purpose and outcomes

BlueGuard is intended to become a Security Monitoring, Detection & Telemetry Assurance platform. An authorized operator should be able to inspect network and endpoint signals, investigate attributed candidate alerts, and understand whether the supporting telemetry was available and timely. The platform must retain uncertainty: a candidate is not proof of compromise, and a healthy observed feed is not proof of complete capture.

| Domain | Product responsibility | Initial boundary |
| --- | --- | --- |
| Monitor | Network records and endpoint inventory/status | Reuse the rc4 Zeek view; add Wazuh endpoint data by a separate contract. |
| Detect | Imported alerts, investigation context, and detection packs | Preserve synthetic demo alerts as synthetic; keep Zeek and Wazuh as independent engines. |
| Assurance | Source-specific freshness, continuity, error, and evidence quality | Preserve rc4 Quality Gate policy v1; version any expanded policy. |

## Commercial hypotheses to validate

These are proposed market and value hypotheses, not validated customer demand or an approved commercial model.

| Hypothesis | Proposal to test with customers |
| --- | --- |
| Primary market and users | MSSPs and corporate SOCs; SOC analysts and security engineers. |
| Potential buyers | SOC managers, CISOs, and security service managers. |
| Differentiation | Integrated security alerts with explicit telemetry assurance context during investigation. |
| Measurable customer value | Reduced investigation effort and shorter telemetry failure detection time, measured against customer baselines and agreed targets. |
| Candidate business models | B2B subscription or annual supported license; licensing and support obligations require separate decisions. |

## Release maturity

| Level | Meaning | Access claim |
| --- | --- | --- |
| **Laboratory Baseline** | Existing v0.5.0-rc4 FastAPI/static UI, Zeek snapshot, restricted ingestion, and Quality Gate. | Private laboratory only; no end-user authentication. |
| **Technical Alpha** | Private internal Zeek/Wazuh integration, normalized imported alerts, first Data Exfiltration Detection Pack, and source-specific Assurance. | Internal validation only; not a customer-ready MVP. |
| **Product MVP** | Authenticated and authorized private single-tenant WebApp with persistent data, operational controls, and a passed customer-access security gate. | Approved customer pilot only. |
| **Commercial Release** | Later licensing, support, operational, and product-readiness obligations resolved. | Separate release decision and evidence required. |

The first proposed customer is a single organization with a named operator and an approved private pilot. Shared multi-tenancy, public exposure, billing, active response, and full SIEM functionality are outside the initial Product MVP. No current repository evidence establishes customer readiness, detection efficacy, reproducible deployment, or commercial licensing rights.
