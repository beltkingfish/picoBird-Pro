"""Background passive bird-call listener.

Records 5-second audio chunks in a loop, runs BirdNET on each, and keeps the
50 most recent detections in memory. Results are show-only (never written to DB).

Usage:
    from server import passive_listener
    passive_listener.start()
    passive_listener.stop()
    passive_listener.get_detections()  # list[dict]
"""

import threading
import logging
from collections import deque
from datetime import datetime, timezone

from server import audio, birdnet

log = logging.getLogger(__name__)

_CHUNK_SECONDS = 5
_MAX_DETECTIONS = 50

_lock       = threading.Lock()
_thread     = None
_stop_event = threading.Event()
_detections: deque = deque(maxlen=_MAX_DETECTIONS)
_status     = "stopped"   # "stopped" | "running" | "error"
_error_msg  = ""


def _listener_loop(device: str) -> None:
    global _status, _error_msg
    with _lock:
        _status = "running"
        _error_msg = ""
    log.info("Passive listener started on %s", device)
    try:
        while not _stop_event.is_set():
            try:
                wav = audio.record_wav(device, duration_s=_CHUNK_SECONDS)
            except RuntimeError as exc:
                log.warning("Passive capture failed: %s", exc)
                _stop_event.wait(2)
                continue

            try:
                results = birdnet.analyze_bytes(wav)
            except Exception as exc:
                log.warning("BirdNET analysis failed during passive listen: %s", exc)
                results = []

            if results:
                ts = datetime.now(timezone.utc).isoformat()
                with _lock:
                    for det in results:
                        _detections.appendleft({**det, "detected_at": ts})
    except Exception as exc:
        log.exception("Passive listener crashed")
        with _lock:
            _status = "error"
            _error_msg = str(exc)
        return
    with _lock:
        _status = "stopped"
    log.info("Passive listener stopped")


def start() -> dict:
    """Start the passive listener thread. Returns current status dict."""
    global _thread, _stop_event
    with _lock:
        if _status == "running":
            return get_status()

    device = audio.get_capture_device()
    if device is None:
        return {"status": "error", "error": "no USB mic found"}

    _stop_event.clear()
    t = threading.Thread(target=_listener_loop, args=(device,), daemon=True)
    with _lock:
        global _thread
        _thread = t
    t.start()
    return {"status": "running", "device": device}


def stop() -> dict:
    """Signal the listener to stop and wait up to 2 s for it to exit."""
    _stop_event.set()
    with _lock:
        t = _thread
    if t and t.is_alive():
        t.join(timeout=_CHUNK_SECONDS + 2)
    return get_status()


def get_status() -> dict:
    with _lock:
        return {
            "status": _status,
            "error":  _error_msg if _status == "error" else None,
        }


def get_detections() -> list:
    with _lock:
        return list(_detections)
