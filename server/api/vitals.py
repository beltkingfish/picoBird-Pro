"""System & database vitals endpoint — powers the PicoCalc Settings screen."""

import shutil
import logging
from flask import Blueprint, jsonify

from server.database import fetchone
from server import vitals as v

log = logging.getLogger(__name__)

bp = Blueprint("vitals", __name__)


@bp.get("/")
def get_vitals():
    """GET /api/vitals — live system + birding stats as JSON."""
    db = v._db_stats()  # {lifers, obs_today, last_bird, last_time}

    species_count = 0
    total_obs = 0
    try:
        row = fetchone("SELECT COUNT(*) AS n FROM species")
        species_count = row["n"] if row else 0
        row = fetchone("SELECT COUNT(*) AS n FROM observations")
        total_obs = row["n"] if row else 0
    except Exception as exc:
        log.warning("vitals DB count failed: %s", exc)

    disk_free_gb = None
    try:
        usage = shutil.disk_usage("/")
        disk_free_gb = round(usage.free / (1024 ** 3), 1)
    except Exception:
        pass

    return jsonify({
        "cpu":           v._cpu_temp(),
        "mem":           v._mem_pct(),
        "uptime":        v._uptime(),
        "ap_clients":    v._ap_clients(),
        "lifers":        db.get("lifers", 0),
        "obs_today":     db.get("obs_today", 0),
        "last_bird":     db.get("last_bird", ""),
        "last_time":     db.get("last_time", ""),
        "species_count": species_count,
        "total_obs":     total_obs,
        "disk_free_gb":  disk_free_gb,
        "birdnet_ok":    v._birdnet_ok(),
    })
