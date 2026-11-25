from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .schemas import Alert, AlertPage, Severity, Status, Summary
from .store import load_demo_alerts
from .zeek_api import router as zeek_router
from .telemetry_health import router as telemetry_router
from .publisher_health import router as publisher_router
from .ingestion_health import router as ingestion_router
from .telemetry_quality import router as quality_router
from .zeek import get_zeek_snapshot

VERSION = "0.5.0-rc4"
BASE = Path(__file__).resolve().parent
ALERTS = load_demo_alerts()

# These demo APIs have no authentication. They MUST remain accessible only
# through the local SSH tunnel, never through a public Ingress/LoadBalancer.
app = FastAPI(
    title="BlueGuard API — lab",
    version=VERSION,
    description="Synthetic alerts and an imported Zeek snapshot; no live sensor integrations.",
    docs_url=None,
    redoc_url=None,
)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
app.include_router(zeek_router)
app.include_router(telemetry_router)
app.include_router(publisher_router)
app.include_router(ingestion_router)
app.include_router(quality_router)


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
    try:
        count = len(get_zeek_snapshot())
    except (OSError, ValueError):
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "zeek_snapshot": "unavailable",
            },
        )
    return {
        "status": "ready",
        "data_mode": "synthetic_alerts_and_zeek_snapshot",
        "zeek_snapshot_records": count,
    }


@app.get("/api/v1/status", response_model=Status, tags=["monitoring"])
def status():
    return Status(
        service="BlueGuard API",
        version=VERSION,
        environment="lab",
        monitoring="snapshot_only",
        zeek_connected=False,
        wazuh_connected=False,
        source="synthetic_alerts_and_zeek_snapshot",
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
