"""USB audio device discovery and capture via ALSA arecord."""

import os
import re
import subprocess
import tempfile
import logging

log = logging.getLogger(__name__)

_RATE    = 22050
_CHANNELS = 1
_FORMAT  = "S16_LE"


def find_usb_mic() -> "str | None":
    """Return the first USB audio capture device as an ALSA hw: string, or None."""
    try:
        out = subprocess.check_output(["arecord", "-l"], stderr=subprocess.DEVNULL,
                                      text=True, timeout=5)
    except Exception:
        return None

    for line in out.splitlines():
        if "usb" in line.lower() or "rode" in line.lower() or "wireless" in line.lower():
            m = re.search(r"card (\d+).*device (\d+)", line, re.IGNORECASE)
            if m:
                return "hw:{},{}".format(m.group(1), m.group(2))

    # Fall back to the first capture card if none matched the USB/Rode hint.
    for line in out.splitlines():
        m = re.search(r"card (\d+).*device (\d+)", line, re.IGNORECASE)
        if m:
            return "hw:{},{}".format(m.group(1), m.group(2))

    return None


def get_capture_device() -> "str | None":
    """Return AUDIO_DEVICE env var if set, else auto-detect via find_usb_mic()."""
    override = os.environ.get("AUDIO_DEVICE", "").strip()
    if override:
        return override
    return find_usb_mic()


def record_wav(device: str, duration_s: int = 10) -> bytes:
    """Record *duration_s* seconds from ALSA *device*, return WAV bytes.

    Raises RuntimeError on capture failure.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp = f.name
    try:
        result = subprocess.run(
            [
                "arecord",
                "-D", device,
                "-f", _FORMAT,
                "-r", str(_RATE),
                "-c", str(_CHANNELS),
                "-d", str(duration_s),
                tmp,
            ],
            capture_output=True,
            timeout=duration_s + 10,
        )
        if result.returncode != 0:
            log.error("arecord failed: %s", result.stderr.decode(errors="replace"))
            raise RuntimeError("arecord exited with code {}".format(result.returncode))
        with open(tmp, "rb") as f:
            return f.read()
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError("audio capture error: {}".format(exc)) from exc
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
