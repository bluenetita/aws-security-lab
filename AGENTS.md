# BlueGuard repository instructions

## Project overview and repository structure

BlueGuard is a controlled AWS network security monitoring laboratory based on EC2, k3s, Zeek, a restricted SSH ingestion path, and a FastAPI application with a static dashboard. Treat recorded deployment and experiment results as historical evidence, not as live status or proof of production readiness. The demo alerts are synthetic; the Zeek connection records are periodic telemetry. Consult `docs/PROJECT_STATE.md` at the start of each task for the current version, Git baseline, validation results, limitations, and work in progress. Keep changing project status in that document rather than in these standing instructions.

| Path | Responsibility |
| --- | --- |
| `applications/blueguard-api/` | FastAPI and static UI sources, fixtures, regression tests, Dockerfiles, dependency lists, and Kubernetes lab baseline. |
| `applications/blueguard-api/k8s/` | Kustomize base and control-plane overlay; the v0.2.0 YAML is historical. |
| `blue-team/zeek/` | Sensor configuration, collector, policies, and systemd units. |
| `infrastructure/blueguard-pipeline/control-plane/` | Restricted receiver and publisher host pipeline. |
| `infrastructure/` | AWS and historical infrastructure material. |
| `scripts/` | Source manifest utility and operational helpers; inspect a helper before running it. |
| `docs/` | Architecture, security, verification, limitations, operations, release context, and current state in `PROJECT_STATE.md`. |
| `evidence/` | Selected structured observations and terminal excerpts, not live telemetry. |
| `.github/workflows/blueguard-ci.yml` | Source-integrity, test, image-build, and Kustomize checks. |
| `MANIFEST.sha256` | SHA-256 inventory of canonical indexed Git blobs. |

The API and UI share one container and Pod. Zeek, the collector, receiver, and publisher run as host services. The application reads a published, read-only snapshot through a lab `hostPath`; it does not query AWS directly.

## Development conventions

- Keep changes focused on the requested component and preserve the existing API, health, and telemetry-quality contracts unless the task explicitly changes them. Add or adjust regression coverage when behavior changes.
- Keep the host pipeline, Zeek sensor, application, and Kubernetes responsibilities distinct. Do not describe periodic collection or UI polling as live streaming.
- Use the existing Python, static-asset, Docker, and Kustomize layouts. Follow adjacent code conventions rather than introducing a new framework or toolchain without a documented need.
- Preserve line-ending rules in `.gitattributes`: LF for shell scripts, service files, and YAML; CRLF for PowerShell files. Avoid unrelated formatting churn.
- Treat the control-plane overlay as a specific laboratory configuration. Do not apply the historical v0.2.0 manifest or the Kustomize base by itself.

## Standard workflow

1. **Inspect:** Read `docs/PROJECT_STATE.md`, relevant source and documentation, and the working-tree status before acting.
2. **Plan:** Define the requested scope, affected trust boundaries, validation, and any authorization needed for external or Git operations.
3. **Implement:** Make focused changes without overwriting unrelated work.
4. **Validate:** Run checks suited to the changed layer and record actual results and limitations.
5. **Review:** Inspect the diff, security implications, and evidence; obtain the required code review before merging.
6. **Document:** Update affected documentation and `docs/PROJECT_STATE.md` when an approved change alters project state.

## Security requirements and least privilege

- Keep credentials, private keys, tokens, kubeconfigs, raw packet captures, operational stores, backups, and personal configuration out of the repository and task context. Respect `.gitignore`, but inspect intended changes before publication because ignore rules are not a security review.
- Preserve the restricted, source-bound SSH ingestion model, pinned server identity, forced receiver command, private writable store, and separately published read-only snapshot. Do not broaden accounts, file permissions, network access, or writable paths without a reviewed security reason.
- Preserve the application container's non-root identity, read-only root filesystem, dropped capabilities, disabled privilege escalation, `RuntimeDefault` seccomp profile, disabled service-account token automount, and read-only telemetry mount.
- Keep the unauthenticated API private behind `ClusterIP` and an operator-controlled SSH tunnel. Do not add a public Ingress or LoadBalancer before authentication and authorization are designed and reviewed. `ClusterIP` alone is not pod-level isolation; verify network controls before asserting segmentation.
- Design any future AWS collector outside FastAPI with an approved read-only IAM role and explicit no-data and authorization-error states. Never embed long-lived AWS credentials in source or images.
- Apply least privilege to CI and operational changes. Treat network metadata and evidence as potentially sensitive before sharing them externally.

## Testing and validation requirements

- Select checks that match the changed layer and report exactly what ran, where, and with what result. Do not turn historical results into claims about a new checkout or deployment.
- For application behavior, run the regression suite from `applications/blueguard-api/` with the existing development requirements in an authorized environment. The CI workflow uses `Dockerfile.test` and runs the QA image without network access, with a read-only filesystem, a temporary `/tmp`, dropped capabilities, and no privilege escalation.
- For build or manifest changes, follow `.github/workflows/blueguard-ci.yml`: verify `MANIFEST.sha256`, build the QA and application images without publishing, render `applications/blueguard-api/k8s/overlays/control-plane`, and check the expected lab resource and security fields. Image builds use `--pull` and may require network access; do not run them when offline operation is required.
- Read `docs/PROJECT_STATE.md` for the current validation record and its provenance. Reconcile stale claims only with attributable run evidence; do not infer reproducible provisioning or end-to-end validation from CI success.
- For documentation-only changes, check factual consistency, paths, links, and scope. An `AGENTS.md`-only change does not necessarily trigger CI; the subsequent required `MANIFEST.sha256` update is within the current workflow path triggers. Use an explicitly authorized manual run if CI validation is required before that update.

## Git workflow and code review requirements

- Work on a scoped branch and inspect the working-tree status and diff before proposing changes. Do not overwrite existing user changes or include unrelated files.
- Present code, infrastructure, security, and documentation changes for review with the relevant test evidence and residual limitations. Obtain a maintainer review before merging; seek focused security review for changes to trust boundaries, permissions, network exposure, or sensitive data handling.
- For a significant architectural change, record the decision, alternatives considered, and tradeoffs in `docs/decisions.md` or a linked decision record before implementation is considered complete.
- Do not stage, commit, push, merge, publish, or deploy merely to complete a local edit. Perform those actions only when the task explicitly authorizes them. Do not claim a check passed unless its output or run record supports the claim.

## Source integrity manifest regeneration

`scripts/source_manifest.py` hashes canonical Git blob contents from the index, excluding `MANIFEST.sha256` itself. It does not hash arbitrary unstaged working-tree content and is not a signature or proof of authorship.

After the intended changes have been reviewed and staging is authorized, stage only those files, then run from the repository root:

```bash
python3 scripts/source_manifest.py --write
git add -- MANIFEST.sha256
python3 scripts/source_manifest.py --check
```

Inspect the staged diff and manifest entry for each intended file before committing. Regenerate the manifest again if the staged content changes. Do not regenerate or stage it during a review-only task; newly added files must be included in the later authorized manifest update.

## Documentation maintenance requirements

- Update the relevant `README.md` and `docs/` pages when behavior, topology, security posture, validation status, or limitations change. Keep application and Kubernetes local READMEs aligned with the root-level documentation.
- Update `docs/PROJECT_STATE.md` when an approved change alters the version, validated Git baseline, evidence, security posture, development phase, or pending work. Record provenance and dates; do not silently promote a proposal or historical result to a verified current fact.
- Distinguish implemented rc4 behavior, planned work, historical observations, user-provided results, and newly verified results. Preserve dates and provenance for experimental claims; do not invent capabilities, measurements, or assurance.
- Keep `docs/architecture.md`, `docs/security.md`, `docs/limitations.md`, `docs/source-availability.md`, and verification guidance consistent with code and evidence. Record remaining risks, including incomplete capture, bounded storage, single-node dependencies, absent application authorization, and unverified end-to-end reproducibility.

## Restrictions on external operations

- Default to repository-local, read-only inspection. Do not access credentials, backups, personal configuration, or files outside the repository while handling repository tasks.
- Do not use the Internet, install software, query AWS or a live cluster, start or stop infrastructure, create Traffic Mirroring sessions, expose services, publish artifacts, or perform deployment without explicit task authorization. Review `scripts/` and `docs/operations.md` before any separately authorized operational work.
- Do not send repository content, evidence, or network metadata to an external service without explicit authorization and a sensitive-data review.

## Definition of done

A change is ready for review when its scope is clear, relevant checks have passed or their absence is stated, security and least-privilege constraints are preserved, documentation and `docs/PROJECT_STATE.md` match the implementation, and the diff contains only intended files. Before a later authorized commit, the staged source manifest must pass `--check`. Report unresolved risks and distinguish repository validation from deployment or production assurance.
