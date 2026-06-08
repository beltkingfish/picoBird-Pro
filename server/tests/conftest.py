"""Shared pytest fixtures for the picoBird Pro server.

Points the database layer at an isolated temp file (via PICOBIRD_DB) *before*
importing any server module, then resets the schema before every test so cases
never bleed into each other.
"""

import os
import tempfile

# Must be set before importing server.database — DB_PATH is read at import time.
_TMPDIR = tempfile.mkdtemp(prefix="picobird-test-")
os.environ["PICOBIRD_DB"] = os.path.join(_TMPDIR, "test.db")

import pytest

from server import database
from server.main import create_app


def _wipe_db():
    """Delete the sqlite file (and WAL/SHM siblings) and recreate the schema."""
    for suffix in ("", "-wal", "-shm"):
        path = database.DB_PATH + suffix
        if os.path.exists(path):
            os.remove(path)
    database.db_init()


@pytest.fixture(autouse=True)
def fresh_db():
    """Give every test a clean schema."""
    _wipe_db()
    yield
    # Leave the file in place between tests; next test wipes it.


@pytest.fixture
def app():
    application = create_app()
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def seed_species(rows):
    """Insert species rows and rebuild the FTS index.

    rows: iterable of (species_code, common_name, sci_name, family_name)
    """
    with database.get_db() as conn:
        conn.executemany(
            """
            INSERT INTO species(species_code, common_name, sci_name, family_name)
            VALUES(?, ?, ?, ?)
            """,
            rows,
        )
        conn.execute("INSERT INTO species_fts(species_fts) VALUES('rebuild')")


@pytest.fixture
def species_fixture():
    """A small, realistic taxonomy slice."""
    rows = [
        ("amerob", "American Robin",   "Turdus migratorius", "Thrushes"),
        ("eurrob1", "European Robin",  "Erithacus rubecula", "Old World Flycatchers"),
        ("baleag",  "Bald Eagle",      "Haliaeetus leucocephalus", "Hawks, Eagles"),
        ("norcar",  "Northern Cardinal","Cardinalis cardinalis", "Cardinals"),
        ("houspa",  "House Sparrow",   "Passer domesticus", "Old World Sparrows"),
    ]
    seed_species(rows)
    return rows
