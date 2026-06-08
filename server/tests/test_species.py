"""Species search — FTS, prefix matching, and region filtering."""

import pytest

from server import database


def _codes(resp):
    return {r["species_code"] for r in resp.get_json()["results"]}


def test_search_empty_query_returns_empty(client, species_fixture):
    resp = client.get("/api/species/search?q=")
    assert resp.status_code == 200
    assert resp.get_json()["results"] == []


def test_search_prefix_match(client, species_fixture):
    # "rob" should prefix-match both robins via FTS.
    resp = client.get("/api/species/search?q=rob")
    assert resp.status_code == 200
    assert _codes(resp) == {"amerob", "eurrob1"}


def test_search_matches_scientific_name(client, species_fixture):
    resp = client.get("/api/species/search?q=turdus")
    assert _codes(resp) == {"amerob"}


def test_search_no_match(client, species_fixture):
    resp = client.get("/api/species/search?q=penguin")
    assert resp.get_json()["results"] == []
    assert resp.get_json()["total"] == 0


def _set_region(codes):
    """Directly populate the region cache + setting (bypasses eBird)."""
    with database.get_db() as conn:
        conn.execute("DELETE FROM region_species")
        conn.executemany(
            "INSERT OR IGNORE INTO region_species(species_code, region_code) VALUES(?, 'US-XX')",
            [(c,) for c in codes],
        )
        conn.execute(
            "INSERT INTO settings(key,value) VALUES('region','US-XX') "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value"
        )


def test_search_region_filter_restricts_results(client, species_fixture):
    # Only the American Robin is "in region".
    _set_region(["amerob"])
    resp = client.get("/api/species/search?q=rob")
    assert _codes(resp) == {"amerob"}   # European Robin filtered out
    assert resp.get_json()["total"] == 1


def test_search_region_set_but_cache_empty_falls_back(client, species_fixture):
    # Regression: a region row with an empty region_species table must NOT
    # blank every search (it previously did).
    with database.get_db() as conn:
        conn.execute(
            "INSERT INTO settings(key,value) VALUES('region','US-XX') "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value"
        )
        # region_species intentionally left empty
    resp = client.get("/api/species/search?q=rob")
    assert _codes(resp) == {"amerob", "eurrob1"}   # unfiltered fallback
