# Security controls and residual risk

This is a **laboratory configuration**, not a customer-facing security service. The existence of a control below is based on the observed setup; it does not imply comprehensive hardening.

## Implemented controls

| Boundary | Implemented control | Residual consideration |
|---|---|---|
| Zeek network path | Traffic Mirroring filter and EC2 Security Groups | Coverage depends on source ENI, filter, enabled session and capture performance |
| Sensor identity | Dedicated `blueguard-sender` account and Ed25519 key | Requires protected private key and lifecycle rotation |
| SSH server identity | Pinned host key in root-managed `known_hosts` | Host-key changes require authenticated revalidation |
| SSH authorization | `from=10.20.1.9`, `restrict`, forced receiver command | Scope depends on SSH/SG configuration; keep accounts nonprivileged |
| Receiver writes | JSONL validation, deduplication, lock and atomic replace | Bounded store; errors can block ingestion |
| Store separation | Private receiver store; publisher-created file with read-only group access | Host-local file permissions and node dependency |
| Publisher service | `systemd` oneshot, `PrivateNetwork`, `ProtectSystem` and scoped writable paths | Publisher still executes as root for controlled publication |
| Application container | non-root UID/GID 10001, read-only filesystem, all capabilities dropped, no privilege escalation, `seccomp: RuntimeDefault`, token automount disabled | Does not replace application security review |
| Kubernetes access | Private `ClusterIP` and operator SSH tunnel; no public Ingress | App has no user-facing login or per-customer authorization; no NetworkPolicies in namespace at rc4 review |
| Credentials in this archive | Placeholder local config; no private key or live token intended | Review metadata and evidence before any public push |

An unauthorized SSH command (`id`) was rejected with exit code 126 in the restricted-receiver test. This is a targeted authorization check, not a full penetration test.

## Controls not yet established

- End-user authentication/MFA, application authorization and multi-tenant isolation.
- Production TLS termination, customer access gateway, network policy and end-to-end access auditing.
- Backup/restore with recovery objectives, automated retention and secure data erasure.
- Automated alerting for ingestion lag, collector/publisher failures, file limits or unexpected sensor silence. rc4 exposes quality/health assessments but does not alert or verify sensor connectivity.
- Continuous deployment, vulnerability scanning, image provenance, registry and immutable image-digest deployment. The project owner reports that BlueGuard CI run #3 passed on consolidated commit `caa8ce1`, but CI did not deploy or validate the recovered host pipeline, Zeek policies, or fresh end-to-end AWS behavior.
- Validated detection/correlation rules and Wazuh ingestion into BlueGuard.

**Deployment constraint:** do not publish the current API via a public LoadBalancer or Ingress until authentication and authorization are implemented. The presence of synthetic alerts must not be presented as detection evidence.

## rc4 release and frontend safeguards

The parallel Canary used a distinct selector and loopback-only port-forwarding. It inherited the read-only Zeek mount and existing container restrictions; it was deleted after promotion. The QA container ran as UID/GID 10001 with no network, read-only filesystem, dropped capabilities and `no-new-privileges`. The Quality Gate UI uses external JS/CSS under the existing CSP, `textContent` for dynamic content, response validation, a 10 s request timeout and stale-value clearing on request failure. UI smoke tests covered asset availability and security headers, not all browser behavior.

The planned rc5 AWS collector must be separate from FastAPI, use an approved read-only IAM role, avoid long-lived credentials in images or repository, and retain explicit authorization-error and missing-data states. No new IAM policy or role has been created by the recorded rc4 work.
