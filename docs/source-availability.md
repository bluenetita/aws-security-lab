# Source inventory and reproducibility

## Included in this repository

- [`applications/blueguard-api/`](../applications/blueguard-api/) preserves original **v0.2.0** application source, Dockerfile, dependency manifests, synthetic alert fixture, tests and Kubernetes manifest.
- `blue-team/zeek/` contains selected Zeek configuration fragments and the historical Zeek service unit.
- AWS, Kubernetes and PowerShell examples are retained for reference; several represent earlier experimental states.
- Evidence files summarize results of **v0.4.2 runtime tests** and network experiments.

## Not included

The supplied archive did **not** contain the deployed **v0.4.2** source tree, image, new manifest or the installed ingestion programs:

| Required component | Known laboratory location |
|---|---|
| BlueGuard v0.4.2 app and Dockerfile | `/home/ubuntu/blueguard-v0.3.0/` on Control Plane |
| Kubernetes v0.4.2 manifest | `k8s/blueguard-v0.4.2.yaml` in that directory |
| Collector source/installed program | Zeek host: `/usr/local/libexec/blueguard-zeek-collector` |
| SSH receiver / JSONL ingestion | Control Plane: `/usr/local/libexec/blueguard-ssh-receiver`, `/usr/local/libexec/blueguard-ingest-jsonl` |
| Publisher source/installed program | Control Plane: `/usr/local/libexec/blueguard-zeek-publisher` |
| Actual service/timer units | Respective EC2 host under `systemd` unit directories |

The directory name `blueguard-v0.3.0` is historical; the deployed application reported version **`0.4.2-lab`**. Deployment outcomes are documented without claiming that the complete release is reproducible from this ZIP.

## Requirements for a source-complete release

1. Export only approved source files and unit definitions from the target hosts; exclude `backups/`, `.smoke/`, local credentials, private keys, `/var/lib` stores and logs.
2. Compare exported sources to the deployed image and the effective manifest; review all configuration differences.
3. Commit the reviewed v0.4.2 sources with automated tests and provenance. Re-run build, unit/integration tests and Kubernetes rollout against the committed code.
4. Update the release documentation only after a source-identical image has been validated.

This is a **reproducibility gap**, not evidence that the currently deployed application failed. The original v0.2.0 code must not be relabeled v0.4.2.
