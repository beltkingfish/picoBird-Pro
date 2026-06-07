"""Shared request-validation helpers for the API blueprints."""


def clamp_int(value, default, lo, hi):
    """Parse *value* to int and clamp to [lo, hi]; return default if unparseable."""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def parse_float(value):
    """Parse to float or return None."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# Bounds used across endpoints.
MAX_LIMIT  = 100
MAX_OFFSET = 100_000
MAX_PAGE   = 10_000
MAX_DIST   = 500   # km, eBird nearby cap is 50 but allow headroom


def valid_lat(v):
    return v is not None and -90.0 <= v <= 90.0


def valid_lng(v):
    return v is not None and -180.0 <= v <= 180.0
