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

All decisions are scoped to the laboratory version; production design requires a separate architecture/security review.
