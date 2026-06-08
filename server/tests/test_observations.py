"""Observation CRUD + input validation."""


def test_add_observation_creates_lifelist_entry(client, species_fixture):
    resp = client.post("/api/observations/", json={"species_code": "amerob", "count": 2})
    assert resp.status_code == 201
    obs = resp.get_json()
    assert obs["species_code"] == "amerob"
    assert obs["count"] == 2

    # Trigger should have populated the life list.
    lifers = client.get("/api/lifelist/").get_json()["results"]
    assert any(r["species_code"] == "amerob" for r in lifers)


def test_add_observation_missing_species_400(client):
    resp = client.post("/api/observations/", json={"count": 1})
    assert resp.status_code == 400
    assert "species_code" in resp.get_json()["error"]


def test_add_observation_malformed_body_400_not_500(client):
    # Regression: get_json(force=True) used to 500 on a non-JSON body.
    resp = client.post("/api/observations/", data="not json",
                       content_type="text/plain")
    assert resp.status_code == 400


def test_add_observation_unknown_species_400(client):
    # Foreign key violation → client error, not a crash.
    resp = client.post("/api/observations/", json={"species_code": "nope999"})
    assert resp.status_code == 400


def test_update_and_delete_observation(client, species_fixture):
    obs_id = client.post(
        "/api/observations/", json={"species_code": "amerob", "count": 1}
    ).get_json()["id"]

    resp = client.patch(f"/api/observations/{obs_id}", json={"count": 5, "notes": "pair"})
    assert resp.status_code == 200
    assert resp.get_json()["count"] == 5

    resp = client.delete(f"/api/observations/{obs_id}")
    assert resp.status_code == 204
    assert client.get(f"/api/observations/{obs_id}").status_code == 404


def test_update_observation_nothing_to_update_400(client, species_fixture):
    obs_id = client.post(
        "/api/observations/", json={"species_code": "amerob"}
    ).get_json()["id"]
    resp = client.patch(f"/api/observations/{obs_id}", json={"unknown": 1})
    assert resp.status_code == 400


def test_list_observations_filter_by_session(client, species_fixture):
    sid = client.post("/api/sessions/", json={"name": "Morning"}).get_json()["id"]
    client.post("/api/observations/", json={"species_code": "amerob", "session_id": sid})
    client.post("/api/observations/", json={"species_code": "baleag"})  # no session

    rows = client.get(f"/api/observations/?session_id={sid}").get_json()
    assert len(rows) == 1
    assert rows[0]["species_code"] == "amerob"
