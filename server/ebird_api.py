"""eBird API v2 client."""

import os
import time
import requests
from typing import Any

BASE_URL = "https://api.ebird.org/v2"
API_KEY  = os.environ.get("EBIRD_API_KEY", "")


def key_present() -> bool:
    """True if an eBird API key is configured."""
    return bool(API_KEY)


# Simple in-process TTL cache to avoid hammering the API.
_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 3600  # seconds


def _get(path: str, params: dict | None = None) -> Any:
    if not API_KEY:
        raise RuntimeError("EBIRD_API_KEY environment variable not set")

    cache_key = path + str(sorted((params or {}).items()))
    if cache_key in _cache:
        ts, data = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return data

    resp = requests.get(
        BASE_URL + path,
        params=params,
        headers={"X-eBirdApiToken": API_KEY},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    _cache[cache_key] = (time.time(), data)
    return data


# ---------------------------------------------------------------------------
# Species
# ---------------------------------------------------------------------------

def species_list(region: str = "world") -> list[dict]:
    """Full eBird taxonomy (optionally filtered to a region)."""
    return _get("/ref/taxonomy/ebird", {"fmt": "json", "locale": "en"})


def species_info(species_code: str) -> dict | None:
    """Return the taxonomy entry for one species code."""
    data = _get("/ref/taxonomy/ebird", {"fmt": "json", "species": species_code})
    return data[0] if data else None


# ---------------------------------------------------------------------------
# Recent observations
# ---------------------------------------------------------------------------

def recent_observations(region: str, max_results: int = 100) -> list[dict]:
    return _get(f"/data/obs/{region}/recent", {"maxResults": max_results})


def nearby_observations(
    lat: float, lng: float, dist_km: int = 25, max_results: int = 100
) -> list[dict]:
    return _get(
        "/data/obs/geo/recent",
        {"lat": lat, "lng": lng, "dist": dist_km, "maxResults": max_results},
    )


def nearby_notable(
    lat: float, lng: float, dist_km: int = 25
) -> list[dict]:
    return _get("/data/obs/geo/recent/notable", {"lat": lat, "lng": lng, "dist": dist_km})


# ---------------------------------------------------------------------------
# Checklists
# ---------------------------------------------------------------------------

def checklist(sub_id: str) -> dict:
    return _get(f"/product/checklist/view/{sub_id}")


def top100(region: str, date: str) -> list[dict]:
    """date format: YYYY-MM-DD"""
    y, m, d = date.split("-")
    return _get(f"/product/top100/{region}/{y}/{m}/{d}")


# ---------------------------------------------------------------------------
# Hotspots
# ---------------------------------------------------------------------------

def nearby_hotspots(lat: float, lng: float, dist_km: int = 25) -> list[dict]:
    return _get("/ref/hotspot/geo", {"lat": lat, "lng": lng, "dist": dist_km, "fmt": "json"})


def hotspot_info(loc_id: str) -> dict:
    return _get(f"/ref/hotspot/info/{loc_id}")
