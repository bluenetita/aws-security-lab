# BlueGuard project state

State record: 25 November 2026. This file describes a versioned laboratory baseline and reported validation, not live infrastructure status. Read it with `AGENTS.md` at the start of a task. CI run details below were supplied by the project owner; this record does not independently verify the GitHub Actions run.

## 1. Project identity and scope

BlueGuard is an experimental AWS network security monitoring laboratory. Its current design combines EC2 and k3s, Zeek traffic observation, restricted incremental ingestion, a published telemetry snapshot, and a FastAPI application with a static dashboard and Telemetry Quality Gate. It is not established as a production SIEM, intrusion detection service, managed SOC, or customer-ready application. The seven dashboard alert examples are synthetic and distinct from Zeek connection telemetry.

Positioning BlueGuard in the future as a commercial **Security Monitoring, Detection & Telemetry Assurance** platform is a proposal for evaluation, not an approved product requirement or a claim about current capabilities.

## 2. Current validated baseline

| Item | Recorded state | Provenance |
| --- | --- | --- |
| Source version | `v0.5.0-rc4` | Repository documentation and project-owner confirmation. |
| Validated commit | `caa8ce1` | Project-owner CI report for this state update. |
| Branch | `chore/consolidate-blueguard-rc4` | Local Git inspection and project-owner confirmation. |
| Integration status | No merge into `main` has been performed. | Project-owner report as of this state record. |

The validated application baseline is the source revision associated with the reported CI result. That result does not validate later documentation changes or establish bit-for-bit image reproducibility, reproducible infrastructure provisioning, or a fresh end-to-end AWS deployment.

## 3. Implemented architecture and capabilities

The documented rc4 architecture has one FastAPI and static-UI container in a single k3s Pod, exposed through a private `ClusterIP` Service and operator-controlled SSH tunnel. Zeek runs on a separate EC2 sensor. A host collector transfers Zeek connection records to a restricted SSH receiver on the Control Plane; a host publisher creates a read-only snapshot and health files for the application. Collection and dashboard refresh are periodic, not continuous streaming. The Control Plane overlay uses a node-local image and a read-only `hostPath` mount.

The rc4 application includes connection, publisher, ingestion, and Telemetry Quality Gate assessments. Historical release evidence records the Quality Gate as deployed, while the repository CI result establishes source-level checks only. Wazuh integration and automated CloudWatch collection are not implemented. The application does not directly query AWS.

## 4. Validation status and evidence

| Check | Result | Evidence and scope |
| --- | --- | --- |
| GitHub Actions | BlueGuard CI run **#3**, successful in **36 seconds**. | Project-owner report for commit `caa8ce1`; the run was not queried during this offline update. |
| Regression suite | **54 passed, 1 warning**, in **0.54 seconds**. | Project-owner report of the CI result; not a fresh local test run. |
| Source integrity | **143 canonical Git checksums verified**. | Project-owner report of the CI manifest check for `caa8ce1` only; later documentation changes are outside that check. |
| QA container build | Successful. | Project-owner report of CI run #3. |
| Application container build | Successful. | Project-owner report of CI run #3; the image was not published by that workflow. |
| Kustomize | Rendering and configured baseline checks successful. | Project-owner report of CI run #3 for the control-plane lab overlay; no apply or deployment is implied. |

CI run #2 failed because tests were excluded from the Docker build context. The issue was resolved by creating `applications/blueguard-api/Dockerfile.test.dockerignore`, according to the project owner. The current workflow verifies the source manifest before the builds, runs the QA image in an isolated container, builds the application image, and checks the rendered Kustomize baseline.

Historical AWS release evidence is recorded in `README.md`, `docs/telemetry-quality.md`, `docs/verification.md`, and `evidence/2026-11-24/result.json`. The original rc4 container image and recovery archives are preserved outside Git, according to the recovery record and project-owner report; they are not reproducibility evidence for this checkout. All four AWS laboratory instances were confirmed stopped on **25 November 2026**, with no Traffic Mirroring sessions remaining at the time of inspection. This is historical evidence, not a current live-state assertion.

The repository documentation records run #3 separately from historical AWS release evidence. Its successful result applies to `caa8ce1`, based on the project-owner report, and must not be extended to later changes without a new validation record.

## 5. Security posture

Documented controls include source-bound Ed25519 SSH ingestion, a pinned server host key, a forced receiver command, separation of the private ingestion store from the published read-only snapshot, and a container configured for non-root execution with a read-only root filesystem, dropped capabilities, no privilege escalation, `RuntimeDefault` seccomp, disabled service-account token automount, and a read-only telemetry mount. The CI workflow grants read-only repository permissions and does not persist checkout credentials.

The API has no end-user authentication or authorization and must remain private. `ClusterIP` does not itself provide pod-level network isolation; no NetworkPolicies were present in the namespace at the rc4 review. The deployment depends on one Pod, node-local images, and host-local data. These controls and gaps are documented laboratory observations, not a fresh security assessment or production assurance. See `docs/security.md` and `docs/architecture.md` for the trust boundaries.

## 6. Known limitations and technical debt

- The `StarletteDeprecationWarning` concerning `httpx` and `TestClient` remains open technical debt; it did not fail the reported 54-test run.
- Host pipeline validation and Zeek policy validation for the recovered sources remain pending.
- Reproducible provisioning, bit-for-bit image reproducibility, and fresh end-to-end AWS validation remain pending.
- The image base digest and transitive dependencies are not yet pinned for reproducible builds, according to `docs/source-availability.md` and `docs/limitations.md`.
- Ingestion capacity and retention are bounded; there is no high-availability data layer. Incomplete mirroring and Zeek gaps have been observed historically, so complete capture is not guaranteed.
- The current application lacks customer identity, authorization, tenant isolation, and validated detection or Wazuh ingestion. Automated CloudWatch collection is still planned work.

## 7. Current development phase

The consolidated rc4 application baseline is validated by the reported CI checks on `caa8ce1`. Configuration of the AI-assisted development workflow is in progress. No merge into `main` has occurred. Later documentation changes remain outside the validated CI commit; future checks must identify their own source revision and evidence. Host pipeline, Zeek policy, reproducibility, and fresh end-to-end validation remain open.

## 8. Next proposed milestones

These are proposed steps, not approved work or completed results:

1. Complete the AI-assisted development workflow configuration and, when authorized, regenerate `MANIFEST.sha256` from the intended staged index before a later commit.
2. Validate the recovered host pipeline and Zeek policies with scoped tests and recorded results.
3. Define reproducible provisioning and pin the image base digest and transitive dependencies; test image reproducibility rather than assuming it.
4. Plan and authorize a controlled fresh end-to-end AWS trace, including cost and Traffic Mirroring cleanup, before claiming that validation.
5. Resolve the `httpx`/`TestClient` deprecation and decide the next security and product requirements before broader exposure.

## 9. Open architectural and product decisions

- Determine whether commercial Security Monitoring, Detection & Telemetry Assurance positioning is appropriate and, if so, define validated customer outcomes and an approved product scope.
- Define identity, authorization, tenant isolation, auditing, and network segmentation requirements before any public application access.
- Decide how to replace node-local images and `hostPath` storage, including retention, recovery objectives, and high availability.
- Define the proposed separate read-only AWS collector, its data contract, IAM boundary, and missing-data/error states before implementation.
- Decide what telemetry quality or detection claims can be supported by controlled evidence, given observed mirror loss and snapshot-based assessments.

Significant architectural decisions should record the selected approach, alternatives, and tradeoffs in `docs/decisions.md` or a linked decision record.

## 10. State maintenance rules

- Read this file at task start. Update it when an approved change alters the source baseline, CI evidence, implementation, security posture, limitations, development phase, or pending work.
- Attach dates, commit or run identifiers, and evidence locations when available. Label project-owner reports, repository evidence, historical observations, fresh verification, and proposals distinctly; do not silently promote one category into another.
- Keep historical AWS shutdown and deployment observations dated. Recheck live resources only in a separately authorized operation; never infer present status from this file.
- Keep standing agent rules in `AGENTS.md` and changing technical status here. Reconcile affected `README.md` and `docs/` pages when authorized, without inventing implementation or validation results.
- Do not store secrets, raw captures, personal configuration, or external backup material in this document.
