# Kubernetes manifests

The Kubernetes files bundled in this repository document the **v0.1.0 and v0.2.0 laboratory stages**.

- `../../applications/blueguard-api/k8s/blueguard-v0.2.0.yaml`: original namespace/Deployment/ClusterIP Service.
- `legacy/blueguard-v0.1.0.yaml`: initial deployment snapshot.
- `../../applications/blueguard-api/k8s/overlays/control-plane/`: Kustomize overlay from the earlier stage; not independently validated as part of the v0.4.2 rollout.

The verified **v0.4.2** Deployment runs a single Pod containing FastAPI **and** static UI, pinned to the Control Plane with a read-only Zeek `hostPath` volume. Its effective manifest was located on the Control Plane but **not supplied in the archive**. See [architecture](../../docs/architecture.md) and [source inventory](../../docs/source-availability.md).

**Do not deploy these historical manifests as the latest BlueGuard release.**
