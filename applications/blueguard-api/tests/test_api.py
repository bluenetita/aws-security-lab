from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_status_does_not_claim_live_connections():
    data = client.get("/api/v1/status").json()
    assert data["monitoring"] == "demo_only"
    assert data["source"] == "synthetic_fixture"
    assert data["zeek_connected"] is False
    assert data["wazuh_connected"] is False


def test_synthetic_alert_list_and_search():
    r = client.get("/api/v1/alerts")
    assert r.status_code == 200
    page = r.json()
    assert page["total"] == 7
    assert all(a["provenance"] == "synthetic" for a in page["items"])
    high = client.get("/api/v1/alerts?severity=high").json()
    assert high["total"] == 2
    search = client.get("/api/v1/alerts?q=192.0.2.41").json()
    assert search["total"] == 1


def test_pagination_and_validation():
    first = client.get("/api/v1/alerts?limit=2&offset=0").json()
    second = client.get("/api/v1/alerts?limit=2&offset=2").json()
    assert len(first["items"]) == 2
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert client.get("/api/v1/alerts?limit=999").status_code == 422
    assert client.get("/api/v1/alerts?severity=bogus").status_code == 422


def test_alert_detail_not_found():
    assert client.get("/api/v1/alerts/BG-DEMO-007").status_code == 200
    assert client.get("/api/v1/alerts/unknown").status_code == 404


def test_no_real_sensors():
    response = client.get("/api/v1/sensors")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_dashboard_and_headers():
    response = client.get("/")
    assert response.status_code == 200
    assert "MODALITA DEMO" in response.text
    assert "Content-Security-Policy" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
