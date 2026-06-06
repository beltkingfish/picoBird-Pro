"""Species search and lookup endpoints."""

import math
from flask import Blueprint, request, jsonify
from server.database import fetchall, fetchone, get_db
from server import ebird_api

bp = Blueprint("species", __name__)

PAGE_SIZE = 20


@bp.get("/search")
def search():
    """
    GET /api/species/search?q=robin&page=0

    Searches local FTS index first; falls back to eBird taxonomy if the local
    DB has no species loaded yet.
    """
    q    = request.args.get("q", "").strip()
    page = int(request.args.get("page", 0))

    if not q:
        return jsonify({"results": [], "total": 0, "page": page})

    # FTS search
    fts_q = " ".join(f"{w}*" for w in q.split())
    rows = fetchall(
        """
        SELECT s.species_code, s.common_name, s.sci_name, s.family_name
        FROM species_fts f
        JOIN species s ON s.species_code = f.species_code
        WHERE species_fts MATCH ?
        ORDER BY rank
        LIMIT ? OFFSET ?
        """,
        (fts_q, PAGE_SIZE, page * PAGE_SIZE),
    )
    total_rows = fetchone(
        "SELECT COUNT(*) AS n FROM species_fts WHERE species_fts MATCH ?",
        (fts_q,)
    )
    total = total_rows["n"] if total_rows else 0

    return jsonify({
        "results":   rows,
        "total":     total,
        "page":      page,
        "page_size": PAGE_SIZE,
        "pages":     math.ceil(total / PAGE_SIZE),
    })


@bp.get("/<code>")
def get_species(code: str):
    """GET /api/species/<species_code>"""
    row = fetchone("SELECT * FROM species WHERE species_code = ?", (code,))
    if row:
        return jsonify(row)

    # Not cached locally — try eBird.
    try:
        info = ebird_api.species_info(code)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    if not info:
        return jsonify({"error": "species not found"}), 404

    return jsonify({
        "species_code": info["speciesCode"],
        "common_name":  info["comName"],
        "sci_name":     info["sciName"],
        "order_name":   info.get("order", ""),
        "family_name":  info.get("familyComName", ""),
    })


@bp.post("/sync")
def sync_taxonomy():
    """
    POST /api/species/sync
    Pulls the full eBird taxonomy into the local SQLite DB + FTS index.
    Can take 10-30 s on first run.
    """
    try:
        taxonomy = ebird_api.species_list()
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    upserted = 0
    with get_db() as conn:
        for entry in taxonomy:
            conn.execute(
                """
                INSERT INTO species(species_code, common_name, sci_name, order_name, family_name)
                VALUES(?,?,?,?,?)
                ON CONFLICT(species_code) DO UPDATE SET
                    common_name = excluded.common_name,
                    sci_name    = excluded.sci_name,
                    order_name  = excluded.order_name,
                    family_name = excluded.family_name,
                    cached_at   = strftime('%s','now')
                """,
                (
                    entry["speciesCode"],
                    entry["comName"],
                    entry["sciName"],
                    entry.get("order", ""),
                    entry.get("familyComName", ""),
                ),
            )
            upserted += 1
        # Rebuild FTS index.
        conn.execute("INSERT INTO species_fts(species_fts) VALUES('rebuild')")

    return jsonify({"synced": upserted})


@bp.get("/nearby")
def nearby():
    """GET /api/species/nearby?lat=&lng=&dist=25"""
    try:
        lat  = float(request.args["lat"])
        lng  = float(request.args["lng"])
        dist = int(request.args.get("dist", 25))
    except (KeyError, ValueError):
        return jsonify({"error": "lat and lng are required"}), 400

    try:
        obs = ebird_api.nearby_observations(lat, lng, dist)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    # Deduplicate by species code.
    seen: set[str] = set()
    species: list[dict] = []
    for o in obs:
        code = o.get("speciesCode", "")
        if code and code not in seen:
            seen.add(code)
            species.append({"species_code": code, "common_name": o.get("comName", "")})

    return jsonify({"results": species, "location": {"lat": lat, "lng": lng, "dist_km": dist}})
