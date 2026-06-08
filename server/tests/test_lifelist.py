"""Life list CSV import — name matching, idempotency, and stats."""

import io


def _post_csv(client, text):
    return client.post(
        "/api/lifelist/import",
        data={"file": (io.BytesIO(text.encode("utf-8")), "list.csv")},
        content_type="multipart/form-data",
    )


def test_import_matches_by_scientific_name(client, species_fixture):
    csv = (
        "Scientific Name,Common Name\n"
        "Turdus migratorius,American Robin\n"
        "Haliaeetus leucocephalus,Bald Eagle\n"
    )
    resp = _post_csv(client, csv)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["added"] == 2
    assert body["skipped"] == 0
    assert body["unmatched"] == 0


def test_import_matches_by_common_name_when_sci_absent(client, species_fixture):
    csv = "Common Name\nNorthern Cardinal\n"
    body = _post_csv(client, csv).get_json()
    assert body["added"] == 1


def test_import_is_idempotent(client, species_fixture):
    csv = "Scientific Name\nTurdus migratorius\n"
    first = _post_csv(client, csv).get_json()
    assert first["added"] == 1
    second = _post_csv(client, csv).get_json()
    assert second["added"] == 0
    assert second["skipped"] == 1


def test_import_counts_unmatched(client, species_fixture):
    csv = "Scientific Name\nAptenodytes forsteri\n"   # Emperor Penguin, not seeded
    body = _post_csv(client, csv).get_json()
    assert body["added"] == 0
    assert body["unmatched"] == 1


def test_import_dedupes_within_one_file(client, species_fixture):
    csv = (
        "Scientific Name\n"
        "Turdus migratorius\n"
        "Turdus migratorius\n"
    )
    body = _post_csv(client, csv).get_json()
    assert body["added"] == 1
    assert body["skipped"] == 1


def test_import_requires_file(client):
    resp = client.post("/api/lifelist/import", data={})
    assert resp.status_code == 400


def test_stats_after_import(client, species_fixture):
    _post_csv(client, "Scientific Name\nTurdus migratorius\nCardinalis cardinalis\n")
    stats = client.get("/api/lifelist/stats").get_json()
    assert stats["total_species"] == 2
