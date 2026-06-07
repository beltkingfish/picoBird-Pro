"""BirdNET-Analyzer integration — runs inference on WAV clips.

Targets the modern birdnet_analyzer package (installed via
`pip install /opt/BirdNET-Analyzer`), invoked as a module:
    python -m birdnet_analyzer.analyze INPUT -o OUTPUT_DIR --rtype csv ...
The legacy root-level `analyze.py` script no longer exists.
"""

import os
import sys
import csv
import glob
import subprocess
import tempfile
import importlib.util

# Path to the BirdNET-Analyzer installation (kept for reference / cwd).
BIRDNET_DIR = os.environ.get("BIRDNET_DIR", "/opt/BirdNET-Analyzer")
MIN_CONF    = float(os.environ.get("BIRDNET_MIN_CONF", "0.5"))


def _birdnet_available() -> bool:
    """True if the birdnet_analyzer package is importable in this interpreter."""
    try:
        return importlib.util.find_spec("birdnet_analyzer") is not None
    except Exception:
        return False


def _pick(row: dict, *names: str) -> str:
    """Case-insensitive fetch of the first matching column from a CSV row."""
    lowered = {k.lower().strip(): v for k, v in row.items() if k}
    for n in names:
        v = lowered.get(n.lower())
        if v is not None and v != "":
            return v
    return ""


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

    Each detection: {"common_name": str, "sci_name": str,
                     "confidence": float, "start_s": float, "end_s": float}
    """
    if not _birdnet_available():
        raise RuntimeError(
            "birdnet_analyzer package not installed. "
            "Run setup/install.sh (pip install /opt/BirdNET-Analyzer)."
        )

    with tempfile.TemporaryDirectory() as out_dir:
        # Use the "table" (BirdNET selection table) writer rather than "csv":
        # the csv writer crashes on empty results (splits an empty species_name
        # column into two). The table writer is a tab-separated .txt and is safe.
        cmd = [
            sys.executable, "-m", "birdnet_analyzer.analyze",
            wav_path,
            "-o",         out_dir,
            "--min_conf", str(min_conf),
            "--rtype",    "table",
        ]
        if lat is not None and lon is not None:
            cmd += ["--lat", str(lat), "--lon", str(lon)]
        if week is not None:
            cmd += ["--week", str(week)]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=BIRDNET_DIR if os.path.isdir(BIRDNET_DIR) else None,
            timeout=90,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "BirdNET failed: {}".format((result.stderr or result.stdout)[:500])
            )

        # The table result type writes one tab-separated .txt per input file.
        table_files = glob.glob(os.path.join(out_dir, "*.txt"))
        if not table_files:
            return []

        detections: list[dict] = []
        for path in table_files:
            with open(path, newline="") as f:
                for entry in csv.DictReader(f, delimiter="\t"):
                    try:
                        conf = float(_pick(entry, "confidence") or 0)
                    except ValueError:
                        conf = 0.0
                    try:
                        start_s = float(_pick(entry, "begin time (s)", "start (s)", "start") or 0)
                    except ValueError:
                        start_s = 0.0
                    try:
                        end_s = float(_pick(entry, "end time (s)", "end (s)", "end") or 3)
                    except ValueError:
                        end_s = 3.0
                    detections.append({
                        "common_name": _pick(entry, "common name", "common_name"),
                        "sci_name":    _pick(entry, "scientific name", "scientific_name", "species code"),
                        "confidence":  round(conf, 4),
                        "start_s":     start_s,
                        "end_s":       end_s,
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
