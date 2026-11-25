# Source inventory and reproducibility

## Included in the uploaded repository (24 November 2026)

The application directory was inspected directly. `applications/blueguard-api/app/main.py` declares `VERSION = "0.4.2-lab"` and imports the Zeek API router. The tree contains `app/zeek.py`, `app/zeek_api.py`, Zeek UI assets, `tests/test_zeek.py`, `tests/test_api.py`, application and QA Dockerfiles, dependency files and synthetic alerts. The Kustomize base uses `localhost/blueguard-api:0.4.2`; the control-plane overlay supplies the lab placement and read-only snapshot. `.github/workflows/blueguard-ci.yml` checks that older baseline. Its presence is not evidence of a successful recent CI run.

Older README text describing this directory as original v0.2.0 was stale. The historical v0.2.0 and v0.1.0 manifests remain examples, not the latest deployment. The Zeek configuration fragments, service unit, AWS examples, PowerShell scripts and historical evidence are also included.

## Not included in the uploaded repository

| Required component | Known laboratory location |
|---|---|
| Complete rc4 application source, static assets, QA tests, Dockerfile | Control Plane: `/home/ubuntu/blueguard-v0.5.0-rc4/` |
| rc3 rollback source | Control Plane: `/home/ubuntu/blueguard-v0.5.0-rc3/` |
| Effective rc4 Deployment/Service and related configuration | k3s namespace `blueguard`; export reviewed resource specs from Control Plane |
| Collector source/installed program | Zeek: `/usr/local/libexec/blueguard-zeek-collector` |
| SSH receiver / JSONL ingestion | Control Plane: `/usr/local/libexec/blueguard-ssh-receiver`, `/usr/local/libexec/blueguard-ingest-jsonl` |
| Publisher source/installed program | Control Plane: `/usr/local/libexec/blueguard-zeek-publisher` |
| Actual service/timer units | Respective EC2 hosts under systemd unit directories |

The deployed image is `localhost/blueguard-api:0.5.0-rc4`; rc3 and rc4 are retained in the node runtime. The release passed 54 tests on the EC2 development tree, and 24 file checksums matched the incremental image. These checks were not rerun on the older uploaded repository. The image layers, full rc4 sources and exact effective manifest are not included by this documentation update.

## Requirements for a source-complete release

1. Export approved rc4 source files, dependency manifests, tests and reviewed service definitions; exclude backups, `.smoke`, credentials, keys, kubeconfig, caches, raw captures and `/var/lib` stores.
2. Export and sanitize effective Kubernetes resource specs; compare to the local manifests and verify the runtime image and configuration. Do not export Kubernetes Secrets.
3. Synchronize the actual rc4 source and tests, deployment manifests and CI checks together; review changes before commit. Never relabel the older source to rc4.
4. Rebuild from the reviewed source with pinned dependencies/base digest, rerun tests and validate an isolated deployment before claiming source-identical reproducibility.

This is a **reproducibility gap**, not an observed failure of the deployed rc4. The 24 November documentation-only overlay intentionally does not change executable source, manifests or CI.
