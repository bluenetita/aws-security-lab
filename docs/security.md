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
| Application container | non-root UID/GID 10001, read-only filesystem, no extra Linux capabilities, `seccomp: RuntimeDefault` | Does not replace application security review |
| Kubernetes access | Private `ClusterIP` and operator SSH tunnel; no public Ingress | App has no user-facing login or per-customer authorization |
| Credentials in this archive | Placeholder local config; no private key or live token intended | Review metadata and evidence before any public push |

An unauthorized SSH command (`id`) was rejected with exit code 126 in the restricted-receiver test. This is a targeted authorization check, not a full penetration test.

## Controls not yet established

- End-user authentication/MFA, application authorization and multi-tenant isolation.
- Production TLS termination, customer access gateway, network policy and end-to-end access auditing.
- Backup/restore with recovery objectives, automated retention and secure data erasure.
- Alerting for ingestion lag, collector/publisher failures, file limits or unexpected sensor silence.
- Formal CI/CD, vulnerability scanning, image provenance, registry and immutable image-digest deployment.
- Validated detection/correlation rules and Wazuh ingestion into BlueGuard.

**Deployment constraint:** do not publish the current API via a public LoadBalancer or Ingress until authentication and authorization are implemented. The presence of synthetic alerts must not be presented as detection evidence.
