"""Smoke tests for the Telemetry Quality Gate dashboard."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_quality_dashboard_section():
    response = client.get("/")

    assert response.status_code == 200

    html = response.text

    for element_id in (
        "telemetry-quality",
        "telemetry-quality-title",
        "quality-status",
        "quality-snapshot",
        "quality-publisher",
        "quality-ingestion",
        "quality-capture",
        "quality-missed",
        "quality-sensor",
        "quality-reasons",
        "quality-note",
        "quality-refresh",
    ):
        assert html.count(f'id="{element_id}"') == 1

    assert "/static/telemetry-quality.js" in html
    assert "/static/telemetry-quality.css" in html

    assert html.index('id="telemetry-quality"') < html.index(
        'id="telemetry-health"'
    )


def test_quality_javascript():
    response = client.get(
        "/static/telemetry-quality.js"
    )

    assert response.status_code == 200

    source = response.text

    assert "/api/v1/telemetry/quality" in source
    assert "validateResponse" in source
    assert "AbortController" in source
    assert "textContent" in source

    assert "innerHTML" not in source
    assert "eval(" not in source

    assert response.headers["Cache-Control"] == "no-store"

    assert response.headers["X-Content-Type-Options"] == "nosniff"

    assert "script-src 'self'" in response.headers[
        "Content-Security-Policy"
    ]


def test_quality_stylesheet():
    response = client.get(
        "/static/telemetry-quality.css"
    )

    assert response.status_code == 200
    assert "text/css" in response.headers["Content-Type"]

    for state in (
        "healthy",
        "degraded",
        "critical",
        "unknown",
        "error",
    ):
        assert (
            f'.telemetry-quality-state[data-state="{state}"]'
            in response.text
        )
