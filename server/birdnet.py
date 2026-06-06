"""BirdNET-Analyzer integration — runs inference on WAV clips."""

import os
import subprocess
import tempfile
import json
from pathlib import Path

# Path to the BirdNET-Analyzer installation.
# Install via: git clone https://github.com/kahst/BirdNET-Analyzer
BIRDNET_DIR  = os.environ.get("BIRDNET_DIR", "/opt/BirdNET-Analyzer")
BIRDNET_BIN  = os.path.join(BIRDNET_DIR, "analyze.py")
MIN_CONF     = float(os.environ.get("BIRDNET_MIN_CONF", "0.5"))


def analyze_clip(
    wav_path: str,
    lat: float | None = None,
    lon: float | None = None,
    week: int | None = None,
    min_conf: float = MIN_CONF,
    num_results: int = 5,
) -> list[dict]:
    """
    Run BirdNET-Analyzer on *wav_path* and return a list of detections.

    Each detection: {"species_code": str, "common_name": str,
                     "sci_name": str, "confidence": float,
                     "start_s": float, "end_s": float}
    """
    if not os.path.isfile(BIRDNET_BIN):
        raise RuntimeError(
            f"BirdNET-Analyzer not found at {BIRDNET_DIR}. "
            "Run setup/install.sh or set BIRDNET_DIR."
        )

    with tempfile.TemporaryDirectory() as tmp:
        out_path = os.path.join(tmp, "results.json")
        cmd = [
            "python3", BIRDNET_BIN,
            "--i",       wav_path,
            "--o",       out_path,
            "--min_conf", str(min_conf),
            "--rtype",   "json",
        ]
        if lat is not None:
            cmd += ["--lat", str(lat), "--lon", str(lon)]
        if week is not None:
            cmd += ["--week", str(week)]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=BIRDNET_DIR,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"BirdNET failed: {result.stderr[:500]}")

        if not os.path.isfile(out_path):
            return []

        raw = json.loads(Path(out_path).read_text())

    detections: list[dict] = []
    for entry in raw:
        detections.append({
            "common_name":   entry.get("common_name", ""),
            "sci_name":      entry.get("scientific_name", ""),
            "confidence":    round(float(entry.get("confidence", 0)), 4),
            "start_s":       entry.get("start_time", 0),
            "end_s":         entry.get("end_time",   3),
        })

    # Sort by confidence descending, return top N.
    detections.sort(key=lambda x: x["confidence"], reverse=True)
    return detections[:num_results]


def analyze_bytes(
    wav_bytes: bytes,
    **kwargs,
) -> list[dict]:
    """Convenience wrapper — write bytes to a temp file then analyze."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_bytes)
        tmp_path = f.name
    try:
        return analyze_clip(tmp_path, **kwargs)
    finally:
        os.unlink(tmp_path)
