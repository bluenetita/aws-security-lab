# Kubernetes manifests

The repository contains historical v0.1.0/v0.2.0 manifests and a v0.5.0-rc4 Kustomize laboratory baseline.

- `../../applications/blueguard-api/k8s/blueguard-v0.2.0.yaml`: original namespace/Deployment/ClusterIP Service.
- `legacy/blueguard-v0.1.0.yaml`: initial deployment snapshot.
- `../../applications/blueguard-api/k8s/overlays/control-plane/`: reconstructed v0.5.0-rc4 lab overlay; fresh deployment validation is pending.

The verified **v0.5.0-rc4** Deployment runs one Pod containing FastAPI and the static UI, pinned to the Control Plane with a read-only Zeek `hostPath` volume. Its effective Deployment and Service specifications were recovered and compared with the reconstructed laboratory manifests on 25 November. The rc4 Canary was deleted following successful promotion. See [architecture](../../docs/architecture.md), [release report](../../docs/telemetry-quality.md) and [source inventory](../../docs/source-availability.md).

**Do not deploy these older manifests as the latest BlueGuard release.**
