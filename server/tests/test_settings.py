"""Region settings — round-trip, clear, and transaction safety."""

import pytest

from server import database
from server.api import settings as settings_mod


def _region_count():
    row = database.fetchone("SELECT COUNT(*) AS n FROM region_species")
    return row["n"] if row else 0


def _region_setting():
    row = database.fetchone("SELECT value FROM settings WHERE key='region'")
    return row["value"] if row else None


def test_get_settings_default_empty(client):
    resp = client.get("/api/settings/")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["region"] == ""
    assert body["region_species_count"] == 0


def test_set_region_caches_species(client, monkeypatch):
    monkeypatch.setattr(
        settings_mod.ebird_api, "region_species_list",
        lambda code: ["amerob", "baleag", "norcar"],
    )
    resp = client.patch("/api/settings/", json={"region": "us-co"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["region"] == "US-CO"          # normalized upper-case
    assert body["species_count"] == 3
    assert _region_count() == 3
    assert _region_setting() == "US-CO"


def test_clear_region(client, monkeypatch):
    monkeypatch.setattr(
        settings_mod.ebird_api, "region_species_list",
        lambda code: ["amerob"],
    )
    client.patch("/api/settings/", json={"region": "US-CO"})
    assert _region_count() == 1

    resp = client.patch("/api/settings/", json={"region": ""})
    assert resp.status_code == 200
    assert resp.get_json()["region"] == ""
    assert _region_count() == 0
    assert _region_setting() is None


def test_unknown_region_returns_404_and_keeps_cache(client, monkeypatch):
    # First set a working region.
    monkeypatch.setattr(
        settings_mod.ebird_api, "region_species_list",
        lambda code: ["amerob", "baleag"],
    )
    client.patch("/api/settings/", json={"region": "US-CO"})
    assert _region_count() == 2

    # eBird returns no species for a bogus region.
    monkeypatch.setattr(
        settings_mod.ebird_api, "region_species_list", lambda code: [],
    )
    resp = client.patch("/api/settings/", json={"region": "ZZ-ZZ"})
    assert resp.status_code == 404
    # Regression: the previously-working cache must be untouched.
    assert _region_count() == 2
    assert _region_setting() == "US-CO"


def test_ebird_failure_does_not_wipe_cache(client, monkeypatch):
    """CRITICAL regression: a failed eBird lookup must not delete a working
    region filter (the DELETE used to run before the network call and commit
    on the early error return)."""
    monkeypatch.setattr(
        settings_mod.ebird_api, "region_species_list",
        lambda code: ["amerob", "baleag", "norcar"],
    )
    client.patch("/api/settings/", json={"region": "US-CO"})
    assert _region_count() == 3

    def boom(code):
        raise RuntimeError("eBird down")

    monkeypatch.setattr(settings_mod.ebird_api, "region_species_list", boom)
    resp = client.patch("/api/settings/", json={"region": "US-NY"})
    assert resp.status_code == 502
    # Cache and setting must still point at the old, working region.
    assert _region_count() == 3
    assert _region_setting() == "US-CO"


def test_patch_without_region_key_400(client):
    resp = client.patch("/api/settings/", json={"foo": "bar"})
    assert resp.status_code == 400
