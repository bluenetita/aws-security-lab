# BlueGuard API v0.2.0 — historical application source

This directory contains the **original v0.2.0** FastAPI source snapshot, not the subsequently deployed v0.4.2 implementation. It is preserved for inspection and historical comparison, **not as the current deployment artifact**.

## Contents

- `app/main.py`: REST endpoints and application entrypoint.
- `app/schemas.py` and `app/store.py`: Pydantic models and synthetic-alert data loader.
- `app/static/`: HTML/CSS/JavaScript dashboard, served by FastAPI.
- `demo/alerts.json`: entirely synthetic alert examples.
- `Dockerfile`, `requirements.txt`: container build dependencies.
- `tests/test_api.py`: local API regression tests.
- `k8s/blueguard-v0.2.0.yaml`: original `ClusterIP` Kubernetes deployment example.

## Local testing (v0.2.0 only)

From this directory, with Python 3.12 or later:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
uvicorn app.main:app --host 127.0.0.1 --port 8080
```

API and dashboard are accessible at `http://127.0.0.1:8080`. Never expose this demonstration application to an untrusted network: it has no end-user authentication or authorization.

Do **not** apply the v0.2.0 Kubernetes manifest to replace a deployed v0.4.2 environment. See [release-source inventory](../../docs/source-availability.md).
