"""Smoke tests for the telemetry dashboard component and its static assets."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_telemetry_dashboard_section():
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="telemetry-health"' in response.text
    assert '/static/telemetry-health.js' in response.text
    assert '/static/telemetry-health.css' in response.text
    assert 'id="telemetry-health-state"' in response.text


def test_telemetry_static_assets():
    for path, expected in (
        ("/static/telemetry-health.js", "/api/v1/telemetry/health"),
        ("/static/telemetry-health.css", ".telemetry-health-panel"),
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert expected in response.text
