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

The original rc4 release passed 54 tests on AWS.
The consolidated repository has not yet passed a fresh CI run.

Kustomize rendering has succeeded locally. No deployment was performed during
the consolidation.

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
2. Execute the application regression suite and OCI builds through CI.
3. Pin the base image digest and transitive dependencies.
4. Validate the recovered host scripts and Zeek policies.
5. Implement reproducible provisioning and deployment procedures.
6. Perform controlled end-to-end validation.

This repository remains a laboratory baseline, not a production-ready release.
