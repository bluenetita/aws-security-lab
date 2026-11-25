# Source inventory and reproducibility

## Consolidated baseline - 25 November 2026

The previous repository contained the v0.4.2-lab application baseline.
The documentation-only update of 24 November described the deployed rc4
release but did not contain its complete operational sources.

The subsequent recovery imported and verified the available rc4 components
from the EC2 laboratory.

| Component | Repository location |
|---|---|
| rc4 application, UI, tests and build definitions | `applications/blueguard-api/` |
| Control Plane telemetry pipeline | `infrastructure/blueguard-pipeline/control-plane/` |
| Zeek collector and sensor configuration | `blue-team/zeek/` |
| Kubernetes laboratory manifests | `applications/blueguard-api/k8s/` |
| Automated application CI | `.github/workflows/blueguard-ci.yml` |

## Recovery provenance

- 38 application, test and build files were recovered.
- 24 application/demo files matched the deployed container during recovery.
- 11 Control Plane operational files were recovered.
- 22 Zeek operational files were recovered.
- Recovery metadata and two Kubernetes resource snapshots were also preserved.
- All 76 exported files passed SHA-256 verification.
- Two trailing-whitespace lines in the recovered application HTML were removed
  before Git integration.
- Linux executable bits and original permissions were recorded.
- Kubernetes manifests were aligned with the observed rc4 configuration.

The original OCI image backup and raw recovery archives remain outside Git.
Kubernetes resource snapshots were used for comparison rather than copied
directly into the deployable manifest tree.

The historical rc3 rollback source was not imported as part of this recovery.

## Validation status

The original rc4 release passed 54 tests on AWS. Separately, the project owner
reports that BlueGuard CI run #3 succeeded in 36 seconds on consolidated commit
`caa8ce1`: 54 tests passed with one warning in 0.54 seconds, 143 canonical Git
checksums were verified, the QA and application images built, and the
Kustomize render and configured baseline checks passed. The earlier CI run #2
failed because tests were excluded from the Docker build context; adding
`applications/blueguard-api/Dockerfile.test.dockerignore` resolved that issue.
The remaining `StarletteDeprecationWarning` concerning `httpx` and `TestClient`
is technical debt. These CI results apply to `caa8ce1`, not to later
documentation changes.

Kustomize rendering also succeeded locally during consolidation. No deployment
was performed during the consolidation or by the CI workflow.

All four laboratory EC2 instances were confirmed stopped on 25 November,
with no Traffic Mirroring sessions remaining in the inspected region.

## Source integrity manifest

`MANIFEST.sha256` records SHA-256 checksums of canonical Git blob
contents, excluding the manifest itself. This avoids differences
caused by Windows and Linux checkout line endings.

After staging intended repository changes, regenerate and verify:

```bash
python3 scripts/source_manifest.py --write
git add -- MANIFEST.sha256
python3 scripts/source_manifest.py --check
```

The manifest verifies indexed content, not arbitrary working-tree
files. It is an integrity consistency check, not a digital signature
or proof of authorship. GitHub Actions verifies it before building
the application.

## Remaining requirements

1. Review source and evidence for confidential information before publication.
2. Pin the base image digest and transitive dependencies; establish bit-for-bit image reproducibility.
3. Validate the recovered host pipeline and Zeek policies.
4. Implement reproducible provisioning and deployment procedures.
5. Perform controlled, fresh end-to-end AWS validation.
6. Resolve the `httpx`/`TestClient` deprecation and assess image scanning and provenance.

This repository remains a laboratory baseline, not a production-ready release.
