"""Life list endpoints."""

from flask import Blueprint, request, jsonify
from server.database import fetchall, fetchone
from server.api._validation import clamp_int, MAX_PAGE

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
