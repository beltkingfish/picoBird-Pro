#!/usr/bin/env python3
"""picoBird Pro — Pi 5 server entry point."""

from flask import Flask
from server.database import db_init
from server.api.species import bp as species_bp
from server.api.observations import bp as observations_bp
from server.api.sessions import bp as sessions_bp
from server.api.lifelist import bp as lifelist_bp
from server.api.sound import bp as sound_bp
from server.api.vitals import bp as vitals_bp
from server.api.settings import bp as settings_bp

VERSION = "1.1.0"


def create_app() -> Flask:
    app = Flask(__name__)

    db_init()

    app.register_blueprint(species_bp,      url_prefix="/api/species")
    app.register_blueprint(observations_bp, url_prefix="/api/observations")
    app.register_blueprint(sessions_bp,     url_prefix="/api/sessions")
    app.register_blueprint(lifelist_bp,     url_prefix="/api/lifelist")
    app.register_blueprint(sound_bp,        url_prefix="/api/sound")
    app.register_blueprint(vitals_bp,       url_prefix="/api/vitals")
    app.register_blueprint(settings_bp,    url_prefix="/api/settings")

    @app.get("/api/ping")
    def ping():
        return {"status": "ok", "app": "picoBird Pro", "version": VERSION}

    return app


if __name__ == "__main__":
    import os
    app = create_app()
    # Dev runner only. Defaults to loopback so it's never accidentally exposed.
    # In production gunicorn binds 127.0.0.1 + 192.168.4.1 (the AP) — see
    # setup/picobird-pro.service — so the API is reachable by the PicoCalc over
    # the AP but never on whatever other network the Pi happens to join.
    host = os.environ.get("PICOBIRD_HOST", "127.0.0.1")
    port = int(os.environ.get("PICOBIRD_PORT", "5000"))
    app.run(host=host, port=port, debug=False)
