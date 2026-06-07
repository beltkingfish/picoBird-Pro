"""
picoBird Pro — PicoCalc client entry point.
Boot order:
  1. Load config.json (WiFi credentials, server address)
  2. Init display + keyboard, show splash + I2C diagnostic
  3. Scan for AP (with retries)
  4. Connect and hand off to UI
"""
import time
import network
import machine
import json

from lib.ili9488 import ILI9488
from lib.keyboard import Keyboard
from app.ui import UI

# ── Defaults (overridden by config.json) ─────────────────────────────────────
AP_SSID_PREFIX = "picoBirdPro"
AP_PASSWORD    = "fieldguide"
API_HOST       = "192.168.4.1"
API_PORT       = 5000

SCAN_RETRIES    = 6
CONNECT_TIMEOUT = 20

C_WHITE = (255, 255, 255)
C_GREEN = (80, 200, 120)
C_RED   = (255, 80, 80)
C_GRAY  = (140, 140, 140)
C_HEAD  = (80, 200, 120)


def _load_config():
    """Load config.json from the filesystem. Returns dict of settings."""
    global AP_PASSWORD, API_HOST, API_PORT, AP_SSID_PREFIX
    try:
        with open("config.json") as f:
            cfg = json.load(f)
        AP_SSID_PREFIX = cfg.get("ap_ssid", AP_SSID_PREFIX)
        AP_PASSWORD    = cfg.get("ap_password", AP_PASSWORD)
        API_HOST       = cfg.get("api_host", API_HOST)
        API_PORT       = int(cfg.get("api_port", API_PORT))
    except Exception:
        pass  # use defaults if config missing or malformed


def _print(display, msg, y, color=C_WHITE):
    display.fill_rect(0, y, 320, 10, 0, 0, 0)
    display.text(msg[:52], 4, y, fg=color)


def _scan_for_ap(display, wlan):
    for attempt in range(1, SCAN_RETRIES + 1):
        _print(display, "Scanning ({}/{})...".format(attempt, SCAN_RETRIES), 70, C_GRAY)
        try:
            nets = wlan.scan()
        except Exception:
            nets = []

        match = None
        for net in nets:
            try:
                ssid = net[0].decode("utf-8")
            except Exception:
                ssid = str(net[0])
            if ssid.startswith(AP_SSID_PREFIX):
                match = ssid
                break

        if match:
            return match

        if attempt == SCAN_RETRIES and nets:
            visible = []
            for net in nets:
                try:
                    visible.append(net[0].decode("utf-8"))
                except Exception:
                    pass
            _print(display, "Visible: " + ", ".join(visible[:3]), 82, C_GRAY)

        wait = min(2 ** (attempt - 1), 8)
        _print(display, "Not found, retry in {}s...".format(wait), 70, C_GRAY)
        time.sleep(wait)

    return None


def _connect(display, wlan, ssid):
    _print(display, "Connecting to {}...".format(ssid), 70, C_WHITE)
    wlan.connect(ssid, AP_PASSWORD)
    deadline = time.time() + CONNECT_TIMEOUT
    while not wlan.isconnected():
        if time.time() > deadline:
            return False
        _print(display, "Waiting for IP...", 82, C_GRAY)
        time.sleep(1)
    ip = wlan.ifconfig()[0]
    _print(display, "IP: " + ip, 82, C_GREEN)
    return True


def main():
    _load_config()

    display = ILI9488()
    kb      = Keyboard()

    # ── Splash ──────────────────────────────────────────────────────────────
    display.fill(0, 0, 0)
    display.text("picoBird Pro", 10, 10, fg=C_HEAD)
    display.fill_rect(0, 26, 320, 1, 40, 100, 60)

    # ── I2C diagnostic ───────────────────────────────────────────────────────
    found = kb.scan()
    if 0x1F in found:
        display.text("Keyboard OK (0x1F)", 4, 36, fg=C_GREEN)
    else:
        addrs = [hex(a) for a in found]
        display.text("KB not found! " + str(addrs), 4, 36, fg=C_RED)

    # ── WiFi ─────────────────────────────────────────────────────────────────
    display.text("Starting WiFi scan...", 4, 56, fg=C_GRAY)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    time.sleep_ms(500)

    if wlan.isconnected():
        wlan.disconnect()
        time.sleep(1)

    connected = False
    ssid = _scan_for_ap(display, wlan)
    if ssid:
        _print(display, "Found: " + ssid, 70, C_GREEN)
        time.sleep_ms(300)
        connected = _connect(display, wlan, ssid)
        if connected:
            _print(display, "Connected!", 56, C_GREEN)
        else:
            _print(display, "DHCP timeout. Offline mode.", 56, C_RED)
    else:
        _print(display, "Pi 5 AP not found.", 70, C_RED)
        _print(display, "Is Pi 5 on & hostapd running?", 82, C_GRAY)
        time.sleep(3)

    time.sleep_ms(800)

    ui = UI(display, kb, API_HOST, API_PORT, connected=connected, ap_ssid=AP_SSID_PREFIX)
    ui.run()


main()
