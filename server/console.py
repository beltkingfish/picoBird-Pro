"""picoBird Pro — local admin console (curses TUI).

Auto-launched on login to the Pi 5's physical console (tty1) only.
SSH sessions are unaffected.

Controls:
  Q        — exit to bash
  R        — restart picoBird services
  S        — stop picoBird services
  T        — trigger eBird taxonomy sync
  L        — show last 20 lines of server log
  (any key to dismiss log view)

Refreshes vitals every 10 seconds automatically.
"""

import curses
import os
import subprocess
import time
import sys
from datetime import datetime

# Re-use vitals collectors from the existing module.
sys.path.insert(0, "/opt/picobird-pro")
from server.vitals import (
    _uptime, _cpu_temp, _mem_pct, _ap_clients,
    _server_ok, _birdnet_ok, _db_stats, _local_ip,
)

REFRESH_S   = 10
SERVICES    = ["picobird-pro", "picobird-vitals", "picobird-pre"]
SERVER_URL  = "http://127.0.0.1:5000"


# ---------------------------------------------------------------------------
# Peripheral detection
# ---------------------------------------------------------------------------

def _on_physical_console() -> bool:
    """True when running on a real TTY (tty1–tty6), not SSH or serial."""
    tty = os.ttyname(sys.stdin.fileno()) if sys.stdin.isatty() else ""
    return any(tty.endswith(f"tty{n}") for n in range(1, 7))


def _hdmi_connected() -> bool:
    """Check /sys/class/drm for a connected display output."""
    drm = "/sys/class/drm"
    if not os.path.isdir(drm):
        return False
    for entry in os.listdir(drm):
        status_path = os.path.join(drm, entry, "status")
        try:
            if open(status_path).read().strip() == "connected":
                return True
        except OSError:
            pass
    return False


def should_launch() -> bool:
    """Only auto-launch on the physical console with a display attached."""
    return _on_physical_console() and _hdmi_connected()


# ---------------------------------------------------------------------------
# Service helpers
# ---------------------------------------------------------------------------

def _systemctl(action: str, services: list[str]) -> str:
    """Run systemctl action on services; return stdout+stderr summary."""
    results = []
    for svc in services:
        try:
            r = subprocess.run(
                ["sudo", "systemctl", action, svc],
                capture_output=True, text=True, timeout=15,
            )
            results.append(f"{svc}: {'ok' if r.returncode == 0 else r.stderr.strip()[:60]}")
        except Exception as exc:
            results.append(f"{svc}: {exc}")
    return "  ".join(results)


def _service_active(name: str) -> bool:
    try:
        r = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() == "active"
    except Exception:
        return False


def _tail_log(lines: int = 20) -> str:
    try:
        r = subprocess.run(
            ["journalctl", "-u", "picobird-pro", "-n", str(lines), "--no-pager"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout or "(no log output)"
    except Exception as exc:
        return str(exc)


def _trigger_sync() -> str:
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{SERVER_URL}/api/species/sync",
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read().decode()[:80]
    except Exception as exc:
        return f"Error: {exc}"


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

COL_TITLE  = 1
COL_GOOD   = 2
COL_WARN   = 3
COL_KEY    = 4
COL_DIM    = 5


def _init_colours():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(COL_TITLE, curses.COLOR_BLACK,  curses.COLOR_CYAN)
    curses.init_pair(COL_GOOD,  curses.COLOR_GREEN,  -1)
    curses.init_pair(COL_WARN,  curses.COLOR_RED,    -1)
    curses.init_pair(COL_KEY,   curses.COLOR_YELLOW, -1)
    curses.init_pair(COL_DIM,   curses.COLOR_WHITE,  -1)


def _dot(ok: bool) -> tuple[str, int]:
    return ("●", COL_GOOD) if ok else ("○", COL_WARN)


def _addstr(win, y: int, x: int, s: str, attr: int = 0):
    """Safe addstr — silently clips if outside window bounds."""
    h, w = win.getmaxyx()
    if y < 0 or y >= h or x < 0 or x >= w:
        return
    try:
        win.addstr(y, x, s[:max(0, w - x)], attr)
    except curses.error:
        pass


def _hline(win, y: int, char: str = "─"):
    h, w = win.getmaxyx()
    if 0 <= y < h:
        try:
            win.addstr(y, 0, char * (w - 1))
        except curses.error:
            pass


# ---------------------------------------------------------------------------
# Main TUI
# ---------------------------------------------------------------------------

def _draw_main(win, status_msg: str = ""):
    win.erase()
    h, w = win.getmaxyx()
    now = datetime.now().strftime("%H:%M:%S")

    # --- Title bar ---
    title = " picoBird Pro — Admin Console "
    _addstr(win, 0, 0, title.ljust(w), curses.color_pair(COL_TITLE) | curses.A_BOLD)
    _addstr(win, 0, w - len(now) - 2, now, curses.color_pair(COL_TITLE))

    row = 2

    # --- System vitals ---
    ip     = _local_ip()
    uptime = _uptime()
    cpu    = _cpu_temp()
    mem    = _mem_pct()

    _addstr(win, row, 2, f"IP: {ip}   up {uptime}   CPU {cpu}   RAM {mem}",
            curses.color_pair(COL_DIM))
    row += 1
    _hline(win, row)
    row += 1

    # --- Service status ---
    _addstr(win, row, 2, "Services", curses.A_BOLD)
    row += 1

    svc_rows = [
        ("picobird-pro",     "API Server"),
        ("picobird-vitals",  "E-ink Display"),
        ("picobird-pre",     "Preflight"),
        ("picobird-button",  "Reset Button"),
        ("hostapd",          "WiFi AP"),
    ]
    clients = _ap_clients()
    for svc, label in svc_rows:
        active = _service_active(svc)
        dot, col = _dot(active)
        state = "running" if active else "stopped"
        extra = f"({clients} client{'s' if clients != 1 else ''})" if svc == "hostapd" and active else ""
        _addstr(win, row, 4, dot, curses.color_pair(col))
        _addstr(win, row, 6, f"{label:<18} {state} {extra}", curses.color_pair(COL_DIM))
        row += 1

    row += 1
    _hline(win, row)
    row += 1

    # --- Birding stats ---
    _addstr(win, row, 2, "Birding", curses.A_BOLD)
    row += 1
    db = _db_stats()
    bnet, bcol = _dot(_birdnet_ok())
    srv,  scol = _dot(_server_ok())

    _addstr(win, row, 4, f"Server {srv}   BirdNET {bnet}",
            curses.color_pair(COL_DIM))
    row += 1
    _addstr(win, row, 4,
            f"Lifers {db['lifers']}   Obs today {db['obs_today']}",
            curses.color_pair(COL_DIM))
    row += 1
    last = f"Last: {db['last_bird']}  {db['last_time']}" if db["last_bird"] else "Last: —"
    _addstr(win, row, 4, last, curses.color_pair(COL_DIM))
    row += 2

    _hline(win, row)
    row += 1

    # --- Key legend ---
    keys = [
        ("R", "Restart services"),
        ("S", "Stop services"),
        ("T", "Sync taxonomy"),
        ("L", "View logs"),
        ("Q", "Exit to shell"),
    ]
    col_w = w // len(keys)
    for i, (key, label) in enumerate(keys):
        x = i * col_w
        _addstr(win, row, x + 1, f"[{key}]", curses.color_pair(COL_KEY) | curses.A_BOLD)
        _addstr(win, row, x + 5, label, curses.color_pair(COL_DIM))
    row += 1

    # --- Status message ---
    if status_msg:
        _addstr(win, row + 1, 2, status_msg[:w - 4], curses.color_pair(COL_WARN))

    _addstr(win, h - 1, 2,
            f"Refreshes every {REFRESH_S}s — ",
            curses.color_pair(COL_DIM))

    win.refresh()


def _show_log(win):
    """Show last 20 log lines; any key to dismiss."""
    log_text = _tail_log(20)
    win.erase()
    h, w = win.getmaxyx()
    _addstr(win, 0, 0,
            " picobird-pro — recent log (any key to close) ".ljust(w),
            curses.color_pair(COL_TITLE) | curses.A_BOLD)
    lines = log_text.splitlines()
    for i, line in enumerate(lines[-( h - 3):]):
        _addstr(win, i + 1, 1, line[:w - 2])
    win.refresh()
    win.getch()


def _run_console(stdscr):
    _init_colours()
    curses.cbreak()
    curses.noecho()
    stdscr.keypad(True)
    stdscr.timeout(REFRESH_S * 1000)  # getch() returns -1 after this many ms

    status = ""

    while True:
        _draw_main(stdscr, status)
        status = ""  # clear after one frame

        key = stdscr.getch()

        if key == -1:
            # Timeout — just refresh
            continue

        ch = chr(key).upper() if 0 < key < 256 else ""

        if ch == "Q":
            break

        elif ch == "R":
            status = "Restarting services..."
            _draw_main(stdscr, status)
            msg = _systemctl("restart", SERVICES)
            status = f"Restart: {msg}"

        elif ch == "S":
            status = "Stopping services..."
            _draw_main(stdscr, status)
            msg = _systemctl("stop", SERVICES)
            status = f"Stop: {msg}"

        elif ch == "T":
            status = "Syncing taxonomy — this may take 20s..."
            _draw_main(stdscr, status)
            result = _trigger_sync()
            status = f"Sync: {result}"

        elif ch == "L":
            _show_log(stdscr)


def main():
    if not should_launch():
        # Not on a physical console or no display — exit silently so
        # /etc/profile.d doesn't disrupt SSH sessions.
        sys.exit(0)

    try:
        curses.wrapper(_run_console)
    except KeyboardInterrupt:
        pass

    # Dropped back to bash.
    print("\npicoBird Pro console closed. Type 'picobird-console' to reopen.\n")


if __name__ == "__main__":
    main()
