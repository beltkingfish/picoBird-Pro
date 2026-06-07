"""Pi 5 pre-flight: init DB and ensure taxonomy is populated.

Runs once at boot via systemd (picobird-pre.service) before the main
Flask server starts. Fast on subsequent boots because it only re-syncs
if the species table is empty.
"""

import os
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s preflight %(message)s")
log = logging.getLogger("preflight")

# Make sure server package is importable from /opt/picobird-pro
sys.path.insert(0, "/opt/picobird-pro")

from server.database import db_init, fetchone


def main():
    log.info("Initialising database...")
    db_init()
    log.info("Database ready at %s", os.environ.get("PICOBIRD_DB", "<default>"))

    row = fetchone("SELECT COUNT(*) AS n FROM species")
    count = row["n"] if row else 0
    log.info("%d species in local taxonomy cache", count)

    if count == 0:
        api_key = os.environ.get("EBIRD_API_KEY", "")
        if not api_key:
            log.warning("EBIRD_API_KEY not set — skipping taxonomy sync on boot")
            log.warning("Run: curl -X POST http://localhost:5000/api/species/sync")
            return

        log.info("Species table empty — syncing eBird taxonomy (this takes ~20 s)...")
        from server import ebird_api
        from server.database import get_db

        # Retry with backoff — a single transient network/API hiccup at boot
        # shouldn't leave species search permanently empty.
        for attempt in range(1, 4):
            try:
                taxonomy = ebird_api.species_list()
                with get_db() as conn:
                    for entry in taxonomy:
                        conn.execute(
                            """
                            INSERT INTO species(species_code, common_name, sci_name, order_name, family_name)
                            VALUES(?,?,?,?,?)
                            ON CONFLICT(species_code) DO UPDATE SET
                                common_name = excluded.common_name,
                                sci_name    = excluded.sci_name
                            """,
                            (
                                entry["speciesCode"],
                                entry["comName"],
                                entry["sciName"],
                                entry.get("order", ""),
                                entry.get("familyComName", ""),
                            ),
                        )
                    conn.execute("INSERT INTO species_fts(species_fts) VALUES('rebuild')")
                log.info("Taxonomy sync complete: %d species", len(taxonomy))
                break
            except Exception as exc:
                if attempt < 3:
                    wait = 2 ** (attempt - 1)  # 1s, 2s
                    log.warning("Taxonomy sync attempt %d failed: %s — retrying in %ds",
                                attempt, exc, wait)
                    time.sleep(wait)
                else:
                    log.error("Taxonomy sync failed after 3 attempts: %s", exc)
                    log.error("Server will start but species search will be empty until synced manually.")
    else:
        log.info("Taxonomy already populated — skipping sync")


if __name__ == "__main__":
    main()
