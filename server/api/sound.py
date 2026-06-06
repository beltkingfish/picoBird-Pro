"""Sound ID endpoint — accepts a WAV upload, returns BirdNET detections."""

from flask import Blueprint, request, jsonify
from server import birdnet

bp = Blueprint("sound", __name__)


@bp.post("/identify")
def identify():
    """
    POST /api/sound/identify
    Body: multipart/form-data with field 'audio' (WAV file)
    Optional query params: lat, lon, week, min_conf
    """
    if "audio" not in request.files:
        return jsonify({"error": "audio file required (field: 'audio')"}), 400

    wav_bytes = request.files["audio"].read()
    if not wav_bytes:
        return jsonify({"error": "empty audio file"}), 400

    try:
        lat      = float(request.args["lat"])  if "lat"      in request.args else None
        lon      = float(request.args["lon"])  if "lon"      in request.args else None
        week     = int(request.args["week"])   if "week"     in request.args else None
        min_conf = float(request.args["min_conf"]) if "min_conf" in request.args else None
    except ValueError:
        return jsonify({"error": "invalid numeric parameter"}), 400

    kwargs = {}
    if lat is not None:      kwargs["lat"]      = lat
    if lon is not None:      kwargs["lon"]      = lon
    if week is not None:     kwargs["week"]     = week
    if min_conf is not None: kwargs["min_conf"] = min_conf

    try:
        detections = birdnet.analyze_bytes(wav_bytes, **kwargs)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503

    return jsonify({"detections": detections})
