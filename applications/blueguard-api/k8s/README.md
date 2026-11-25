# BlueGuard v0.5.0-rc4 Kubernetes baseline (AWS k3s laboratory)

This directory describes the reconstructed **v0.5.0-rc4 laboratory baseline**. The project owner reports successful Kustomize rendering and configured baseline checks in BlueGuard CI run #3 on `caa8ce1`. Fresh end-to-end deployment validation remains pending. See [rc4 release evidence](../../../docs/telemetry-quality.md) and [project state](../../../docs/PROJECT_STATE.md).

## Structure

- `base/`: namespace, Service, shared Deployment configuration.
- `overlays/control-plane/`: lab nodeSelector (existing `node-selector.yaml`), control-plane toleration, Zeek `hostPath` mount, and the Zeek file environment variable.
- `kustomization.yaml`: deliberately resolves to the control-plane **lab overlay**, not the obsolete v0.2.0 manifest.
- `blueguard-v0.2.0.yaml`: retained for historical reference, no longer referenced by Kustomize.

**Do not apply `base/` alone.** The baseline API readiness endpoint requires a readable Zeek snapshot. The lab overlay supplies the mounted snapshot.

## Safety and limitations

- No resource has been applied by this package.
- This baseline still requires `localhost/blueguard-api:0.5.0-rc4` already present on the **control-plane** node (`imagePullPolicy: Never`).
- The API is deliberately pinned to `ip-10-20-1-10`; `hostPath` is local to that node.
- `hostPath` is for this laboratory only. It is not acceptable as a generic production persistence strategy.
- The baseline Deployment is not multi-node highly available. CI run #3 checked the rendered lab overlay at `caa8ce1`, according to the project owner; continuous deployment and a fresh apply were not validated. The observed rc4 namespace had no NetworkPolicies.
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
3. Introduce workload identity, access controls, NetworkPolicies, deployment automation, and tested rollback.
4. Validate the recovered host pipeline and Zeek policies, then perform a separately authorized fresh end-to-end test. Health and quality monitoring already exist in the historical deployed rc4. See [roadmap](../../../docs/roadmap.md).
