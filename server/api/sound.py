"""Sound ID endpoints — on-demand capture, passive listener, and WAV upload."""

import logging
from flask import Blueprint, request, jsonify
from server import birdnet, audio, passive_listener
from server.api._validation import clamp_int

log = logging.getLogger(__name__)

bp = Blueprint("sound", __name__)


@bp.get("/device")
def device():
    """GET /api/sound/device — return detected USB audio capture device."""
    return jsonify({"device": audio.get_capture_device()})


@bp.post("/capture")
def capture():
    """POST /api/sound/capture?duration=10
    Record from the USB mic on the Pi and run BirdNET.
    Returns detections without logging them.
    """
    duration = clamp_int(request.args.get("duration"), default=10, lo=3, hi=30)

    dev = audio.get_capture_device()
    if dev is None:
        return jsonify({"error": "no USB mic found"}), 503

    try:
        wav = audio.record_wav(dev, duration_s=duration)
    except RuntimeError as exc:
        log.warning("Capture failed: %s", exc)
        return jsonify({"error": "audio capture failed: {}".format(exc)}), 503

    try:
        detections = birdnet.analyze_bytes(wav)
    except RuntimeError as exc:
        log.warning("BirdNET analysis failed: %s", exc)
        return jsonify({"error": "sound identification unavailable"}), 503
    except Exception:
        log.exception("Unexpected error during sound identification")
        return jsonify({"error": "internal error during analysis"}), 500

    return jsonify({"device": dev, "duration_s": duration, "detections": detections})


@bp.post("/listen")
def listen():
    """POST /api/sound/listen  body: {"action": "start"|"stop"}
    Start or stop the passive background listener.
    """
    body = request.get_json(silent=True) or {}
    action = body.get("action", "")
    if action == "start":
        result = passive_listener.start()
    elif action == "stop":
        result = passive_listener.stop()
    else:
        return jsonify({"error": "action must be 'start' or 'stop'"}), 400

    if result.get("status") == "error":
        return jsonify(result), 503
    return jsonify(result)


@bp.get("/detections")
def detections():
    """GET /api/sound/detections — recent passive-listener results."""
    status = passive_listener.get_status()
    device = audio.get_capture_device()
    return jsonify({
        "status":     status["status"],
        "device":     device,
        "detections": passive_listener.get_detections(),
    })


@bp.post("/identify")
def identify():
    """POST /api/sound/identify
    Body: multipart/form-data with field 'audio' (WAV file).
    Accepts a client-supplied WAV upload instead of capturing from the Pi mic.
    """
    if "audio" not in request.files:
        return jsonify({"error": "audio file required (field: 'audio')"}), 400

    wav_bytes = request.files["audio"].read()
    if not wav_bytes:
        return jsonify({"error": "empty audio file"}), 400

    try:
        lat      = float(request.args["lat"])      if "lat"      in request.args else None
        lon      = float(request.args["lon"])      if "lon"      in request.args else None
        week     = int(request.args["week"])       if "week"     in request.args else None
        min_conf = float(request.args["min_conf"]) if "min_conf" in request.args else None
    except ValueError:
        return jsonify({"error": "invalid numeric parameter"}), 400

    kwargs = {}
    if lat is not None:      kwargs["lat"]      = lat
    if lon is not None:      kwargs["lon"]      = lon
    if week is not None:     kwargs["week"]     = week
    if min_conf is not None: kwargs["min_conf"] = min_conf

    try:
        dets = birdnet.analyze_bytes(wav_bytes, **kwargs)
    except RuntimeError as exc:
        log.warning("BirdNET analysis failed: %s", exc)
        return jsonify({"error": "sound identification unavailable"}), 503
    except Exception:
        log.exception("Unexpected error during sound identification")
        return jsonify({"error": "internal error during analysis"}), 500

    return jsonify({"detections": dets})
