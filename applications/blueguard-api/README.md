# BlueGuard API v0.4.2-lab — repository source baseline

This directory contains the **v0.4.2-lab** FastAPI application from the uploaded repository, not the subsequently deployed v0.5.0-rc4 implementation. The version is declared in `app/main.py`.

## Contents

- `app/main.py`: REST endpoints and entrypoint.
- `app/schemas.py`, `app/store.py`: Pydantic models and synthetic-alert loader.
- `app/zeek.py`, `app/zeek_api.py`: Zeek snapshot models and API.
- `app/static/`: HTML/CSS/JavaScript dashboard and Zeek connection view.
- `demo/alerts.json`: synthetic alert examples.
- `Dockerfile`, `Dockerfile.test`, dependency manifests: runtime and QA build definitions.
- `tests/test_api.py`, `tests/test_zeek.py`: source-baseline tests.
- `k8s/`: v0.4.2 Kustomize lab baseline and historical v0.2.0 manifest.

## Local testing (repository baseline only)

From this directory with Python 3.12 or later, use a separate environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The repository tests have not been rerun by this documentation update. Running the API requires an appropriate approved Zeek snapshot or fixture as configured by `BLUEGUARD_ZEEK_FILE`; a missing snapshot can make readiness fail. For an authorized lab-only preview, run `uvicorn app.main:app --host 127.0.0.1 --port 8080`. No public exposure: the application lacks end-user authentication and authorization.

**Do not apply the historical manifests to replace the deployed rc4 environment.** See [source inventory](../../docs/source-availability.md) and [rc4 quality policy](../../docs/telemetry-quality.md).
