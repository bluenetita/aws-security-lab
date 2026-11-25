# BlueGuard v0.4.2 Kubernetes baseline (AWS k3s laboratory)

This directory describes the **v0.4.2 repository baseline**, not the deployed v0.5.0-rc4 configuration. Do not apply it over the running release; see [rc4 release evidence](../../../docs/telemetry-quality.md).

## Structure

- `base/`: namespace, Service, shared Deployment configuration.
- `overlays/control-plane/`: lab nodeSelector (existing `node-selector.yaml`), control-plane toleration, Zeek `hostPath` mount, and the Zeek file environment variable.
- `kustomization.yaml`: deliberately resolves to the control-plane **lab overlay**, not the obsolete v0.2.0 manifest.
- `blueguard-v0.2.0.yaml`: retained for historical reference, no longer referenced by Kustomize.

**Do not apply `base/` alone.** The baseline API readiness endpoint requires a readable Zeek snapshot. The lab overlay supplies the mounted snapshot.

## Safety and limitations

- No resource has been applied by this package.
- This baseline still requires `localhost/blueguard-api:0.4.2` already present on the **control-plane** node (`imagePullPolicy: Never`).
- The API is deliberately pinned to `ip-10-20-1-10`; `hostPath` is local to that node.
- `hostPath` is for this laboratory only. It is not acceptable as a generic production persistence strategy.
- The baseline Deployment is not multi-node highly available. A CI workflow is present in the repository, but no successful run or continuous deployment is asserted here. The observed rc4 namespace had no NetworkPolicies.
- The current demo API lacks authentication: keep it private; do **not** expose it through a public Ingress or LoadBalancer.
- A healthy API process does not imply fresh Zeek data. The Zeek sensor may be stopped while the snapshot still exists.

## Review (read-only)

From the application directory on a machine with `kubectl` / Kustomize:

```bash
kubectl kustomize k8s/overlays/control-plane
```

To compare against the live cluster, copy the application `k8s/` tree to a secure directory on the Control Plane and run:

```bash
sudo k3s kubectl diff -k /path/to/k8s/overlays/control-plane
```

`kubectl diff` exits 0 if no differences, 1 for differences, >1 on error. It does not apply the manifest. **Review all differences before considering an apply.** The Namespace and Service are included in the comparison.

## Next architectural tasks

1. Publish immutable container images in an OCI registry and remove the node-local image dependency.
2. Replace the node-local Zeek snapshot `hostPath` with a persistent ingest/data layer.
3. Introduce workload identity, access controls, NetworkPolicies, CI/CD, and tested rollback.
4. Synchronize rc4 sources/manifests and CI; health and quality monitoring already exist in the deployed rc4. See [roadmap](../../../docs/roadmap.md).
