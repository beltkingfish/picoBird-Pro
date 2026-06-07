"""Observation CRUD endpoints."""

import sqlite3
from flask import Blueprint, request, jsonify
from server.database import fetchall, fetchone, execute
from server.api._validation import clamp_int, MAX_LIMIT, MAX_OFFSET

bp = Blueprint("observations", __name__)


@bp.get("/")
def list_observations():
    """GET /api/observations/?session_id=&limit=50&offset=0"""
    session_id = request.args.get("session_id")
    limit      = clamp_int(request.args.get("limit"),  50, 1, MAX_LIMIT)
    offset     = clamp_int(request.args.get("offset"),  0, 0, MAX_OFFSET)

    if session_id:
        rows = fetchall(
            """
            SELECT o.*, s.common_name, s.sci_name
            FROM observations o
            LEFT JOIN species s ON s.species_code = o.species_code
            WHERE o.session_id = ?
            ORDER BY o.observed_at DESC
            LIMIT ? OFFSET ?
            """,
            (session_id, limit, offset),
        )
    else:
        rows = fetchall(
            """
            SELECT o.*, s.common_name, s.sci_name
            FROM observations o
            LEFT JOIN species s ON s.species_code = o.species_code
            ORDER BY o.observed_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
    return jsonify(rows)


@bp.post("/")
def add_observation():
    """POST /api/observations/"""
    data = request.get_json(force=True)
    required = ("species_code",)
    for field in required:
        if field not in data:
            return jsonify({"error": f"missing field: {field}"}), 400

    try:
        row_id = execute(
            """
            INSERT INTO observations(session_id, species_code, count, notes, latitude, longitude, observed_at)
            VALUES(?, ?, ?, ?, ?, ?, COALESCE(?, strftime('%s','now')))
            """,
            (
                data.get("session_id"),
                data["species_code"],
                data.get("count", 1),
                data.get("notes"),
                data.get("latitude"),
                data.get("longitude"),
                data.get("observed_at"),
            ),
        )
    except sqlite3.IntegrityError:
        # Unknown species_code or session_id (foreign key) — client error,
        # not a server crash. Most often: taxonomy not synced yet.
        return jsonify({
            "error": "unknown species_code or session_id (is the taxonomy synced?)"
        }), 400

    row = fetchone("SELECT * FROM observations WHERE id = ?", (row_id,))
    return jsonify(row), 201


@bp.get("/<int:obs_id>")
def get_observation(obs_id: int):
    row = fetchone("SELECT * FROM observations WHERE id = ?", (obs_id,))
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify(row)


@bp.patch("/<int:obs_id>")
def update_observation(obs_id: int):
    data = request.get_json(force=True)
    fields = []
    values = []
    # NOTE: column names here come ONLY from this hardcoded whitelist — never
    # from user input — so the f-string below is not SQL-injectable. Keep it
    # that way: do not interpolate any request-derived keys into the SQL.
    for col in ("count", "notes", "latitude", "longitude"):
        if col in data:
            fields.append(f"{col} = ?")
            values.append(data[col])
    if not fields:
        return jsonify({"error": "nothing to update"}), 400
    values.append(obs_id)
    execute(f"UPDATE observations SET {', '.join(fields)} WHERE id = ?", values)
    row = fetchone("SELECT * FROM observations WHERE id = ?", (obs_id,))
    return jsonify(row)


@bp.delete("/<int:obs_id>")
def delete_observation(obs_id: int):
    execute("DELETE FROM observations WHERE id = ?", (obs_id,))
    return "", 204
