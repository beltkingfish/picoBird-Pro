"""picoBird Pro — e-ink vitals display service.

Runs as a daemon, refreshes the Waveshare 2.9" display every REFRESH_INTERVAL
seconds with a live dashboard:

  ┌─────────────────────────────────────┐  296 x 128 px
  │ picoBird Pro       192.168.4.1   │
  │ up 3h 22m          v1.0          │
  ├─────────────────────────────────────┤
  │ AP ● 2 clients     Server ●       │
  │ CPU 44°C  MEM 38%  BirdNET ●     │
  ├─────────────────────────────────────┤
  │ Lifers 247    Obs today 12        │
  │ Last: American Robin  14:32       │
  └─────────────────────────────────────┘
"""

import os
import re
import time
import signal
import subprocess
import logging
from datetime import datetime, timedelta
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    from server.eink import EPD
    _HW_AVAILABLE = True
except ImportError:
    _HW_AVAILABLE = False

REFRESH_INTERVAL = int(os.environ.get("VITALS_INTERVAL", "30"))  # seconds
DB_PATH          = os.environ.get("PICOBIRD_DB", "/var/lib/picobird-pro/picobird.db")
SERVER_URL       = "http://127.0.0.1:5000/api/ping"
FONT_DIR         = Path(__file__).parent / "fonts"

logging.basicConfig(level=logging.INFO, format="%(asctime)s vitals %(message)s")
log = logging.getLogger("vitals")


# ---------------------------------------------------------------------------
# Data collectors
# ---------------------------------------------------------------------------

def _uptime() -> str:
    try:
        with open("/proc/uptime") as f:
            secs = float(f.read().split()[0])
        td = timedelta(seconds=int(secs))
        h, rem = divmod(td.seconds, 3600)
        m = rem // 60
        days = td.days
        if days:
            return f"{days}d {h}h {m}m"
        return f"{h}h {m}m"
    except Exception:
        return "?"


def _cpu_temp() -> str:
    try:
        raw = Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()
        return f"{int(raw) // 1000}°C"
    except Exception:
        return "?"


def _mem_pct() -> str:
    try:
        lines = Path("/proc/meminfo").read_text().splitlines()
        info  = {}
        for line in lines:
            k, v = line.split(":", 1)
            info[k.strip()] = int(v.strip().split()[0])
        used = info["MemTotal"] - info["MemAvailable"]
        pct  = used * 100 // info["MemTotal"]
        return f"{pct}%"
    except Exception:
        return "?"


def _ap_clients() -> int:
    """Count DHCP leases active on the AP interface."""
    try:
        leases = Path("/var/lib/misc/dnsmasq.leases").read_text().strip()
        return len([l for l in leases.splitlines() if l])
    except Exception:
        return 0


def _server_ok() -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen(SERVER_URL, timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def _birdnet_ok() -> bool:
    birdnet_dir = os.environ.get("BIRDNET_DIR", "/opt/BirdNET-Analyzer")
    return os.path.isfile(os.path.join(birdnet_dir, "analyze.py"))


def _db_stats() -> dict:
    stats = {"lifers": 0, "obs_today": 0, "last_bird": "", "last_time": ""}
    if not os.path.isfile(DB_PATH):
        return stats
    try:
        # Reuse the canonical DB layer (handles connection lifecycle/WAL/etc).
        from server.database import fetchone

        row = fetchone("SELECT COUNT(*) AS n FROM lifelist")
        stats["lifers"] = row["n"] if row else 0

        today_ts = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        row = fetchone(
            "SELECT COUNT(*) AS n FROM observations WHERE observed_at >= ?",
            (today_ts,),
        )
        stats["obs_today"] = row["n"] if row else 0

        row = fetchone(
            """
            SELECT o.observed_at, COALESCE(s.common_name, o.species_code) AS name
            FROM observations o
            LEFT JOIN species s ON s.species_code = o.species_code
            ORDER BY o.observed_at DESC LIMIT 1
            """
        )
        if row:
            stats["last_bird"] = (row["name"] or "")[:22]
            stats["last_time"] = datetime.fromtimestamp(row["observed_at"]).strftime("%H:%M")
    except Exception as exc:
        log.warning("DB stats query failed: %s", exc)
    return stats


def _local_ip() -> str:
    try:
        out = subprocess.check_output(["hostname", "-I"], text=True).strip()
        # Prefer the 192.168.4.x AP address
        for part in out.split():
            if part.startswith("192.168.4."):
                return part
        return out.split()[0]
    except Exception:
        return "?"


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def _load_font(size: int):
    """Try to load DejaVu; fall back to PIL default."""
    candidates = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render_image() -> Image.Image:
    """Collect vitals and render a 296x128 1-bit PIL Image."""
    W, H = 296, 128
    img  = Image.new("1", (W, H), 1)   # white background
    d    = ImageDraw.Draw(img)

    f10 = _load_font(10)
    f11 = _load_font(11)
    f12 = _load_font(12)
    f14 = _load_font(14)

    uptime  = _uptime()
    cpu     = _cpu_temp()
    mem     = _mem_pct()
    clients = _ap_clients()
    server  = _server_ok()
    birdnet = _birdnet_ok()
    db      = _db_stats()
    ip      = _local_ip()
    now     = datetime.now().strftime("%H:%M")

    DOT_ON  = "●"   # filled circle
    DOT_OFF = "○"   # empty circle

    # --- Row 0: title bar ---
    d.rectangle([0, 0, W, 20], fill=0)
    d.text((4, 3),       "picoBird Pro",       font=f12, fill=1)
    d.text((160, 3),     ip,                   font=f12, fill=1)
    d.text((W - 38, 3),  now,                  font=f10, fill=1)

    # --- Row 1: uptime ---
    d.text((4, 23),  f"up {uptime}",            font=f10, fill=0)

    # --- Divider ---
    d.line([(0, 38), (W, 38)], fill=0, width=1)

    # --- Row 2: connectivity ---
    ap_dot  = DOT_ON if clients >= 0 else DOT_OFF
    srv_dot = DOT_ON if server  else DOT_OFF
    bnet_dot= DOT_ON if birdnet else DOT_OFF
    d.text((4,  41), f"AP {ap_dot} {clients} client{'s' if clients != 1 else ''}",
           font=f11, fill=0)
    d.text((160, 41), f"Server {srv_dot}",       font=f11, fill=0)

    # --- Row 3: system ---
    d.text((4,  56), f"CPU {cpu}  MEM {mem}",   font=f11, fill=0)
    d.text((160, 56), f"BirdNET {bnet_dot}",     font=f11, fill=0)

    # --- Divider ---
    d.line([(0, 72), (W, 72)], fill=0, width=1)

    # --- Row 4: birding stats ---
    d.text((4,  75), f"Lifers {db['lifers']}",   font=f11, fill=0)
    d.text((160, 75), f"Obs today {db['obs_today']}", font=f11, fill=0)

    # --- Row 5: last bird ---
    last = f"Last: {db['last_bird']}" if db["last_bird"] else "Last: —"
    t    = db["last_time"]
    d.text((4,  90),      last,                  font=f11, fill=0)
    if t:
        d.text((W - 38, 90), t,                  font=f10, fill=0)

    # --- Border ---
    d.rectangle([0, 0, W - 1, H - 1], outline=0)

    return img


def image_to_bytes(img: Image.Image) -> bytes:
    """Convert PIL 1-bit image to packed bytes for the EPD driver."""
    # EPD expects MSB-first, 0=black 1=white
    return img.tobytes()


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

_running = True


def _handle_signal(sig, frame):
    global _running
    _running = False


def run():
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT,  _handle_signal)

    if not _HW_AVAILABLE:
        log.warning("PIL or RPi.GPIO not available — running in dry-run mode (no display output)")
        while _running:
            img = render_image()
            log.info("[dry-run] frame rendered %dx%d", img.width, img.height)
            for _ in range(REFRESH_INTERVAL * 10):
                if not _running:
                    break
                time.sleep(0.1)
        return

    epd = EPD()
    log.info("Initialising e-ink display...")
    epd.init()
    epd.clear()

    try:
        while _running:
            try:
                img   = render_image()
                buf   = image_to_bytes(img)
                epd.display(buf)
                log.info("Display refreshed")
            except Exception as exc:
                log.error("Render error: %s", exc)

            for _ in range(REFRESH_INTERVAL * 10):
                if not _running:
                    break
                time.sleep(0.1)
    finally:
        epd.clear()
        epd.sleep()
        epd.close()
        log.info("Display sleeping")


if __name__ == "__main__":
    run()
