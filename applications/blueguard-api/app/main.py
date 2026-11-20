from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .schemas import Alert, AlertPage, Severity, Status, Summary
from .store import load_demo_alerts

VERSION = "0.2.0-lab"
BASE = Path(__file__).resolve().parent
ALERTS = load_demo_alerts()

# These demo APIs have no authentication. They MUST remain accessible only
# through the local SSH tunnel, never through a public Ingress/LoadBalancer.
app = FastAPI(
    title="BlueGuard API — demo",
    version=VERSION,
    description="Read-only synthetic data; no live Wazuh or Zeek integration.",
    docs_url=None,
    redoc_url=None,
)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; img-src 'self'; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
    )
    return response


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(BASE / "static" / "index.html")


@app.get("/healthz", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/readyz", tags=["health"])
def ready():
    return {"status": "ready", "data_mode": "synthetic_fixture"}


@app.get("/api/v1/status", response_model=Status, tags=["monitoring"])
def status():
    return Status(
        service="BlueGuard API",
        version=VERSION,
        environment="lab",
        monitoring="demo_only",
        zeek_connected=False,
        wazuh_connected=False,
        source="synthetic_fixture",
        timestamp_utc=datetime.now(timezone.utc),
    )


@app.get("/api/v1/alerts", response_model=AlertPage, tags=["alerts"])
def list_alerts(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    severity: Severity | None = None,
    q: Annotated[str | None, Query(max_length=80)] = None,
):
    matches = list(ALERTS)
    if severity:
        matches = [alert for alert in matches if alert.severity == severity]
    if q:
        needle = q.casefold()
        matches = [alert for alert in matches if any(needle in field.casefold() for field in (
            alert.id, alert.title, str(alert.source_ip), str(alert.destination_ip), alert.reason
        ))]
    return AlertPage(total=len(matches), limit=limit, offset=offset, items=matches[offset:offset+limit])


@app.get("/api/v1/alerts/{alert_id}", response_model=Alert, tags=["alerts"])
def get_alert(alert_id: str):
    for alert in ALERTS:
        if alert.id == alert_id:
            return alert
    raise HTTPException(status_code=404, detail="Alert not found")


@app.get("/api/v1/summary", response_model=Summary, tags=["alerts"])
def summary():
    return Summary(
        total=len(ALERTS),
        by_severity={level: sum(a.severity == level for a in ALERTS) for level in ("low", "medium", "high", "critical")},
        new=sum(a.triage == "new" for a in ALERTS),
        investigating=sum(a.triage == "investigating" for a in ALERTS),
        data_mode="synthetic_fixture",
    )


@app.get("/api/v1/sensors", tags=["monitoring"])
def sensors():
    # No sensor is connected: never invent live telemetry.
    return {"items": [], "source": "none", "message": "No live sensors configured"}
