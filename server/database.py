"""SQLite wrapper — schema init and query helpers."""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.environ.get("PICOBIRD_DB", "/var/lib/picobird-pro/picobird.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS species (
    species_code TEXT PRIMARY KEY,
    common_name  TEXT NOT NULL,
    sci_name     TEXT NOT NULL,
    order_name   TEXT,
    family_name  TEXT,
    cached_at    INTEGER DEFAULT (strftime('%s','now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS species_fts
    USING fts5(species_code UNINDEXED, common_name, sci_name, content='species', content_rowid='rowid');

CREATE TABLE IF NOT EXISTS sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT,
    location   TEXT,
    latitude   REAL,
    longitude  REAL,
    started_at INTEGER DEFAULT (strftime('%s','now')),
    ended_at   INTEGER
);

CREATE TABLE IF NOT EXISTS observations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    species_code TEXT REFERENCES species(species_code),
    count        INTEGER DEFAULT 1,
    notes        TEXT,
    latitude     REAL,
    longitude    REAL,
    observed_at  INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS lifelist (
    species_code TEXT PRIMARY KEY REFERENCES species(species_code),
    first_seen   INTEGER DEFAULT (strftime('%s','now')),
    obs_count    INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS obs_session_idx ON observations(session_id);
CREATE INDEX IF NOT EXISTS obs_species_idx ON observations(species_code);

CREATE TRIGGER IF NOT EXISTS lifelist_upsert
AFTER INSERT ON observations
BEGIN
    INSERT INTO lifelist(species_code, first_seen, obs_count)
        VALUES(NEW.species_code, NEW.observed_at, 1)
    ON CONFLICT(species_code) DO UPDATE
        SET obs_count = obs_count + 1;
END;
"""


def db_init():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db() as conn:
        conn.executescript(SCHEMA)


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def fetchall(sql: str, params=()) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def fetchone(sql: str, params=()) -> dict | None:
    with get_db() as conn:
        row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def execute(sql: str, params=()) -> int:
    """Run a write statement and return lastrowid."""
    with get_db() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid
