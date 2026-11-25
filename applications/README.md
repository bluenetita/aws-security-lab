# Application source

[`blueguard-api/`](blueguard-api/) contains the **v0.5.0-rc4** FastAPI source baseline, Zeek snapshot API/UI, synthetic alert fixtures, application and QA Dockerfiles, tests and Kubernetes examples. This version is declared in the recovered `app/main.py`.

The recovered **v0.5.0-rc4 application source and regression tests are included**. The 54-test release result belongs to the EC2 development tree. Separately, the project owner reports that BlueGuard CI run #3 validated the consolidated application baseline at `caa8ce1` with 54 passing tests, one warning, successful QA and application image builds, and Kustomize checks. The CI result does not validate subsequent documentation changes or a fresh end-to-end deployment. See [source inventory](../docs/source-availability.md) and [project state](../docs/PROJECT_STATE.md).
