"""Life list endpoints."""

import csv
import io
import logging
from flask import Blueprint, request, jsonify
from server.database import fetchall, fetchone, execute, get_db
from server.api._validation import clamp_int, MAX_PAGE

log = logging.getLogger(__name__)

bp = Blueprint("lifelist", __name__)


@bp.get("/")
def get_lifelist():
    """GET /api/lifelist/?page=0"""
    page  = clamp_int(request.args.get("page"), 0, 0, MAX_PAGE)
    limit = 50
    rows  = fetchall(
        """
        SELECT l.species_code, l.first_seen, l.obs_count,
               s.common_name, s.sci_name, s.family_name
        FROM lifelist l
        LEFT JOIN species s ON s.species_code = l.species_code
        ORDER BY l.first_seen DESC
        LIMIT ? OFFSET ?
        """,
        (limit, page * limit),
    )
    total = fetchone("SELECT COUNT(*) AS n FROM lifelist")
    return jsonify({
        "results":   rows,
        "total":     total["n"] if total else 0,
        "page":      page,
        "page_size": limit,
    })


@bp.get("/check/<code>")
def check_species(code: str):
    """GET /api/lifelist/check/<species_code> — quick lifer check."""
    row = fetchone("SELECT * FROM lifelist WHERE species_code = ?", (code,))
    return jsonify({"lifer": row is None, "entry": row})


@bp.post("/import")
def import_csv():
    """POST /api/lifelist/import
    Body: multipart/form-data with field 'file' = eBird life-list CSV export.

    The eBird API cannot return a personal life list, so this imports the CSV
    a user downloads from eBird (My eBird -> Download My Data, or the Life List
    page). Each row is matched against the local taxonomy by scientific name
    (preferred) or common name; matched species missing from the life list are
    inserted. Idempotent — rows already present are skipped.
    """
    if "file" not in request.files:
        return jsonify({"error": "CSV file required (field: 'file')"}), 400

    raw = request.files["file"].read()
    if not raw:
        return jsonify({"error": "empty file"}), 400

    try:
        text = raw.decode("utf-8-sig")
    except Exception:
        try:
            text = raw.decode("latin-1")
        except Exception:
            return jsonify({"error": "could not decode file (expected CSV text)"}), 400

    added = skipped = unmatched = 0
    reader = csv.DictReader(io.StringIO(text))

    # eBird exports vary; accept a few common header spellings.
    def pick(row, *names):
        for n in names:
            for key in row:
                if key and key.strip().lower() == n:
                    return (row[key] or "").strip()
        return ""

    # Preload taxonomy + existing life list once, instead of per-row queries
    # (a real eBird export is hundreds-to-thousands of rows).
    sci_to_code = {}
    common_to_code = {}
    for sp in fetchall("SELECT species_code, sci_name, common_name FROM species"):
        if sp["sci_name"]:
            sci_to_code[sp["sci_name"].lower()] = sp["species_code"]
        if sp["common_name"]:
            common_to_code[sp["common_name"].lower()] = sp["species_code"]
    existing = {
        r["species_code"]
        for r in fetchall("SELECT species_code FROM lifelist")
    }

    to_insert = []
    seen = set()
    for row in reader:
        sci    = pick(row, "scientific name", "sci_name", "scientific_name")
        common = pick(row, "common name", "common_name", "species")
        if not sci and not common:
            continue

        code = sci_to_code.get(sci.lower()) if sci else None
        if not code and common:
            code = common_to_code.get(common.lower())
        if not code:
            unmatched += 1
            continue

        if code in existing or code in seen:
            skipped += 1
            continue
        seen.add(code)
        to_insert.append((code,))
        added += 1

    if to_insert:
        with get_db() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO lifelist(species_code) VALUES(?)",
                to_insert,
            )

    return jsonify({"added": added, "skipped": skipped, "unmatched": unmatched})


@bp.get("/stats")
def stats():
    total   = fetchone("SELECT COUNT(*) AS n FROM lifelist")
    by_fam  = fetchall(
        """
        SELECT s.family_name, COUNT(*) AS species_count
        FROM lifelist l
        LEFT JOIN species s ON s.species_code = l.species_code
        GROUP BY s.family_name
        ORDER BY species_count DESC
        LIMIT 20
        """
    )
    return jsonify({
        "total_species": total["n"] if total else 0,
        "by_family":     by_fam,
    })
