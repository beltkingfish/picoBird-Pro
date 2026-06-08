"""Health-check endpoint."""


def test_ping_ok(client):
    resp = client.get("/api/ping")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert "version" in body
