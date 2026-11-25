"""Static integration checks for publisher health dashboard."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_publisher_panel_is_registered():
    response = client.get("/")

    assert response.status_code == 200

    html = response.text

    required = (
        'id="publisher-health-status"',
        'id="publisher-last-success"',
        'id="publisher-success-age"',
        'id="publisher-sensor-state"',
        "/static/publisher-health.js",
        "/static/publisher-health.css",
    )

    for marker in required:
        assert marker in html


def test_publisher_static_assets_are_served():
    for path in (
        "/static/publisher-health.js",
        "/static/publisher-health.css",
    ):
        response = client.get(path)

        assert response.status_code == 200
        assert len(response.content) > 0
