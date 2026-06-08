"""App settings endpoints — currently: region filter."""

import logging
from flask import Blueprint, request, jsonify
from server.database import fetchone, execute, get_db
from server import ebird_api

log = logging.getLogger(__name__)

bp = Blueprint("settings", __name__)


@bp.get("/")
def get_settings():
    """GET /api/settings/ — return current settings."""
    row = fetchone("SELECT value FROM settings WHERE key='region'")
    region = row["value"] if row else ""
    count_row = fetchone("SELECT COUNT(*) AS n FROM region_species")
    return jsonify({
        "region": region,
        "region_species_count": count_row["n"] if count_row else 0,
    })


@bp.patch("/")
def patch_settings():
    """PATCH /api/settings/ — update settings.

    Body: {"region": "US-CO"}   Set region filter (fetches eBird spplist).
          {"region": ""}        Clear region filter (search all species).
    """
    body = request.get_json(silent=True) or {}

    if "region" not in body:
        return jsonify({"error": "expected {\"region\": \"...\"}"}), 400

    region = (body["region"] or "").strip().upper()

    with get_db() as conn:
        conn.execute("DELETE FROM region_species")
        if region:
            try:
                codes = ebird_api.region_species_list(region)
            except Exception as exc:
                log.warning("eBird spplist(%s) failed: %s", region, exc)
                return jsonify({"error": "eBird lookup failed — check region code"}), 502

            if not codes:
                return jsonify({"error": "no species found for region — check code (e.g. US-CO)"}), 404

            conn.executemany(
                "INSERT OR IGNORE INTO region_species(species_code, region_code) VALUES(?,?)",
                [(c, region) for c in codes],
            )
            conn.execute(
                "INSERT INTO settings(key,value) VALUES('region',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (region,),
            )
            return jsonify({"ok": True, "region": region, "species_count": len(codes)})
        else:
            conn.execute("DELETE FROM settings WHERE key='region'")
            return jsonify({"ok": True, "region": "", "species_count": 0})
