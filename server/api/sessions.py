"""Birding session endpoints."""

from flask import Blueprint, request, jsonify
from server.database import fetchall, fetchone, execute

bp = Blueprint("sessions", __name__)


@bp.get("/")
def list_sessions():
    rows = fetchall("SELECT * FROM sessions ORDER BY started_at DESC LIMIT 100")
    return jsonify(rows)


@bp.post("/")
def create_session():
    data = request.get_json(force=True)
    row_id = execute(
        """
        INSERT INTO sessions(name, location, latitude, longitude)
        VALUES(?, ?, ?, ?)
        """,
        (
            data.get("name"),
            data.get("location"),
            data.get("latitude"),
            data.get("longitude"),
        ),
    )
    row = fetchone("SELECT * FROM sessions WHERE id = ?", (row_id,))
    return jsonify(row), 201


@bp.get("/<int:session_id>")
def get_session(session_id: int):
    row = fetchone("SELECT * FROM sessions WHERE id = ?", (session_id,))
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify(row)


@bp.patch("/<int:session_id>/end")
def end_session(session_id: int):
    execute(
        "UPDATE sessions SET ended_at = strftime('%s','now') WHERE id = ?",
        (session_id,),
    )
    row = fetchone("SELECT * FROM sessions WHERE id = ?", (session_id,))
    return jsonify(row)


@bp.get("/<int:session_id>/summary")
def session_summary(session_id: int):
    session = fetchone("SELECT * FROM sessions WHERE id = ?", (session_id,))
    if not session:
        return jsonify({"error": "not found"}), 404

    species_count = fetchone(
        "SELECT COUNT(DISTINCT species_code) AS n FROM observations WHERE session_id = ?",
        (session_id,),
    )
    obs_count = fetchone(
        "SELECT COUNT(*) AS n FROM observations WHERE session_id = ?",
        (session_id,),
    )
    top_species = fetchall(
        """
        SELECT o.species_code, s.common_name, SUM(o.count) AS total
        FROM observations o
        LEFT JOIN species s ON s.species_code = o.species_code
        WHERE o.session_id = ?
        GROUP BY o.species_code
        ORDER BY total DESC
        LIMIT 10
        """,
        (session_id,),
    )
    return jsonify({
        "session":        session,
        "species_count":  species_count["n"] if species_count else 0,
        "obs_count":      obs_count["n"] if obs_count else 0,
        "top_species":    top_species,
    })
