"""Life list endpoints."""

import csv
import io
import logging
from flask import Blueprint, request, jsonify
from server.database import fetchall, fetchone, execute
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

    for row in reader:
        sci    = pick(row, "scientific name", "sci_name", "scientific_name")
        common = pick(row, "common name", "common_name", "species")
        if not sci and not common:
            continue

        match = None
        if sci:
            match = fetchone(
                "SELECT species_code FROM species WHERE sci_name = ? COLLATE NOCASE",
                (sci,),
            )
        if not match and common:
            match = fetchone(
                "SELECT species_code FROM species WHERE common_name = ? COLLATE NOCASE",
                (common,),
            )
        if not match:
            unmatched += 1
            continue

        code = match["species_code"]
        exists = fetchone("SELECT 1 FROM lifelist WHERE species_code = ?", (code,))
        if exists:
            skipped += 1
            continue
        try:
            execute(
                "INSERT OR IGNORE INTO lifelist(species_code) VALUES(?)",
                (code,),
            )
            added += 1
        except Exception as exc:
            log.warning("lifelist import insert failed for %s: %s", code, exc)
            unmatched += 1

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
