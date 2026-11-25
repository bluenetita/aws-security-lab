"""Static integration tests for the ingestion health dashboard."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_ingestion_panel_is_integrated():
    response = client.get("/")

    assert response.status_code == 200

    html = response.text

    required = (
        'id="ingestion-health-status"',
        'id="ingestion-last-batch"',
        'id="ingestion-batch-age"',
        'id="ingestion-new-records"',
        'id="ingestion-duplicates"',
        'id="ingestion-total-records"',
        'id="ingestion-store-updated"',
        'id="ingestion-health-note"',
        "/static/ingestion-health.js",
        "/static/ingestion-health.css",
    )

    for marker in required:
        assert html.count(marker) == 1

    # Scope the structural check to the Telemetry Health section.
    assert html.count('id="telemetry-health"') == 1

    section_start = html.index('id="telemetry-health"')
    section_end = html.index("</section>", section_start)

    section = html[section_start:section_end]

    assert section.count('class="telemetry-health-footer"') == 1

    assert (
        section.index('id="publisher-health-status"')
        < section.index('id="ingestion-health-status"')
        < section.index('class="telemetry-health-footer"')
    )


def test_ingestion_assets_are_served():
    js = client.get("/static/ingestion-health.js")
    css = client.get("/static/ingestion-health.css")

    assert js.status_code == 200
    assert css.status_code == 200

    assert "/api/v1/telemetry/ingestion" in js.text
    assert "textContent" in js.text
    assert 'data-state="recent"' in css.text
