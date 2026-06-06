#!/usr/bin/env python3
"""picoBird Pro — Pi 5 server entry point."""

from flask import Flask
from server.database import db_init
from server.api.species import bp as species_bp
from server.api.observations import bp as observations_bp
from server.api.sessions import bp as sessions_bp
from server.api.lifelist import bp as lifelist_bp
from server.api.sound import bp as sound_bp

def create_app() -> Flask:
    app = Flask(__name__)

    db_init()

    app.register_blueprint(species_bp,      url_prefix="/api/species")
    app.register_blueprint(observations_bp, url_prefix="/api/observations")
    app.register_blueprint(sessions_bp,     url_prefix="/api/sessions")
    app.register_blueprint(lifelist_bp,     url_prefix="/api/lifelist")
    app.register_blueprint(sound_bp,        url_prefix="/api/sound")

    @app.get("/api/ping")
    def ping():
        return {"status": "ok", "app": "picoBird Pro"}

    return app


if __name__ == "__main__":
    app = create_app()
    # Listen on all interfaces so the PicoCalc can reach us over the AP.
    app.run(host="0.0.0.0", port=5000, debug=False)
