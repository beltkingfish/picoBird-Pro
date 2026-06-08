"""Birding session lifecycle + summary."""


def test_create_and_get_session(client):
    resp = client.post("/api/sessions/", json={"name": "Dawn Chorus"})
    assert resp.status_code == 201
    sid = resp.get_json()["id"]
    assert resp.get_json()["name"] == "Dawn Chorus"
    assert resp.get_json()["ended_at"] is None

    resp = client.get(f"/api/sessions/{sid}")
    assert resp.status_code == 200


def test_create_session_empty_body_ok(client):
    # Regression: get_json(force=True) used to 500 on an empty body.
    resp = client.post("/api/sessions/")
    assert resp.status_code == 201


def test_end_session_sets_ended_at(client):
    sid = client.post("/api/sessions/", json={"name": "X"}).get_json()["id"]
    resp = client.patch(f"/api/sessions/{sid}/end")
    assert resp.status_code == 200
    assert resp.get_json()["ended_at"] is not None


def test_session_summary_counts(client, species_fixture):
    sid = client.post("/api/sessions/", json={"name": "Count"}).get_json()["id"]
    client.post("/api/observations/", json={"species_code": "amerob", "count": 2, "session_id": sid})
    client.post("/api/observations/", json={"species_code": "amerob", "count": 1, "session_id": sid})
    client.post("/api/observations/", json={"species_code": "baleag", "count": 1, "session_id": sid})

    summary = client.get(f"/api/sessions/{sid}/summary").get_json()
    assert summary["species_count"] == 2   # robin + eagle
    assert summary["obs_count"] == 3
    # Robin has the highest total count (3).
    assert summary["top_species"][0]["species_code"] == "amerob"
    assert summary["top_species"][0]["total"] == 3


def test_session_summary_not_found_404(client):
    assert client.get("/api/sessions/999/summary").status_code == 404
