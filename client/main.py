"""picoBird Pro — PicoCalc client boot sequence.

Boot order:
  1. Init display, show splash
  2. Scan for picoBirdPro AP with retries + backoff
  3. Connect and verify server reachable
  4. Launch main menu UI
"""

import time
import network
from machine import SPI, Pin, I2C

from lib.ili9488 import ILI9488
from lib.keyboard import Keyboard
from app.screen import Screen, BLACK, WHITE, GREEN, RED, ACCENT, GRAY
from app.ui import UI
from app.screens.home import HomeScreen

# ---------------------------------------------------------------------------
# Hardware pin constants — adjust to match your PicoCalc wiring
# ---------------------------------------------------------------------------
SPI_ID   = 0
SPI_SCK  = 2
SPI_MOSI = 3
SPI_MISO = 4
DISP_CS  = 5
DISP_DC  = 6
DISP_RST = 7
DISP_BL  = 8

KBD_I2C  = 0
KBD_SDA  = 20
KBD_SCL  = 21

# ---------------------------------------------------------------------------
# Discovery config
# ---------------------------------------------------------------------------
# The client will scan for any SSID that starts with AP_SSID_PREFIX.
# This lets you rename the AP without reflashing (as long as prefix matches).
AP_SSID_PREFIX  = "picoBirdPro"
AP_SSID_EXACT   = "picoBirdPro"   # preferred exact name
AP_PASS         = "fieldguide"

SERVER_PORT     = 5000
PING_PATH       = "/api/ping"

SCAN_ATTEMPTS   = 8    # how many AP scans before giving up
CONNECT_TIMEOUT = 20   # seconds to wait for DHCP
SERVER_TIMEOUT  = 5    # seconds for ping check


# ---------------------------------------------------------------------------
# Display helpers used before the Screen/UI abstraction is ready
# ---------------------------------------------------------------------------

def _splash(s: Screen, msg: str, color: int = WHITE, line: int = 0):
    """Update a single status line on the splash screen."""
    y = 60 + line * 14
    s.fill_rect(0, y, s.width, 14, BLACK)
    s.text(msg[:s.cols], 4, y, color)
    s.show()


# ---------------------------------------------------------------------------
# Network discovery
# ---------------------------------------------------------------------------

def _scan_for_ap(sta, s: Screen) -> str | None:
    """
    Scan for a picoBirdPro AP.
    Returns the SSID to connect to, or None if not found after retries.
    Prefers the exact AP_SSID_EXACT match; falls back to any SSID starting
    with AP_SSID_PREFIX (so you can have picoBirdPro-2 etc).
    """
    for attempt in range(1, SCAN_ATTEMPTS + 1):
        _splash(s, f"Scanning... ({attempt}/{SCAN_ATTEMPTS})", GRAY, 1)
        try:
            nets = sta.scan()  # list of (ssid, bssid, channel, rssi, security, hidden)
        except Exception:
            nets = []

        exact   = None
        partial = None
        for net in nets:
            ssid = net[0].decode("utf-8", "ignore") if isinstance(net[0], bytes) else net[0]
            if ssid == AP_SSID_EXACT:
                exact = ssid
                break
            if ssid.startswith(AP_SSID_PREFIX) and partial is None:
                partial = ssid

        found = exact or partial
        if found:
            _splash(s, f"Found: {found}", GREEN, 1)
            return found

        # Exponential backoff: 1s, 2s, 4s, 4s, 4s ...
        wait = min(2 ** (attempt - 1), 4)
        _splash(s, f"Not found, retry in {wait}s...", GRAY, 1)
        time.sleep(wait)

    return None


def _connect_wifi(sta, ssid: str, s: Screen) -> bool:
    """Connect to *ssid* and wait for DHCP. Returns True on success."""
    _splash(s, f"Connecting to {ssid}...", WHITE, 1)
    sta.connect(ssid, AP_PASS)
    deadline = time.time() + CONNECT_TIMEOUT
    dot = 0
    while not sta.isconnected():
        if time.time() > deadline:
            return False
        dots = "." * ((dot % 4) + 1)
        _splash(s, f"Waiting for IP{dots}", GRAY, 2)
        dot += 1
        time.sleep(0.5)
    ip_info = sta.ifconfig()
    _splash(s, f"IP: {ip_info[0]}", GREEN, 2)
    return True


def _ping_server(host: str, s: Screen) -> bool:
    """Verify the picoBird Pro server is reachable."""
    _splash(s, "Checking server...", GRAY, 3)
    import socket
    import json
    try:
        addr = socket.getaddrinfo(host, SERVER_PORT)[0][-1]
        sock = socket.socket()
        sock.settimeout(SERVER_TIMEOUT)
        sock.connect(addr)
        req = (
            f"GET {PING_PATH} HTTP/1.1\r\n"
            f"Host: {host}:{SERVER_PORT}\r\n"
            f"Connection: close\r\n\r\n"
        )
        sock.send(req.encode())
        resp = b""
        while True:
            chunk = sock.recv(256)
            if not chunk:
                break
            resp += chunk
        sock.close()
        # Look for our JSON payload anywhere in the response
        if b'"picoBird Pro"' in resp:
            return True
        return False
    except Exception:
        return False


def _derive_server_ip(sta) -> str:
    """
    Derive the Pi 5's IP from our gateway address.
    On the picoBirdPro AP the gateway is always the Pi 5 (192.168.4.1).
    """
    try:
        gw = sta.ifconfig()[2]  # gateway
        if gw and gw != "0.0.0.0":
            return gw
    except Exception:
        pass
    return "192.168.4.1"  # fallback


# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------

def main():
    # --- Hardware init ---
    spi = SPI(
        SPI_ID,
        baudrate=40_000_000,
        polarity=0, phase=0,
        sck=Pin(SPI_SCK),
        mosi=Pin(SPI_MOSI),
        miso=Pin(SPI_MISO),
    )
    display = ILI9488(
        spi,
        cs=Pin(DISP_CS,  Pin.OUT),
        dc=Pin(DISP_DC,  Pin.OUT),
        rst=Pin(DISP_RST, Pin.OUT),
        bl=Pin(DISP_BL,  Pin.OUT),
        width=320, height=320,
    )
    i2c      = I2C(KBD_I2C, sda=Pin(KBD_SDA), scl=Pin(KBD_SCL), freq=100_000)
    keyboard = Keyboard(i2c)
    screen   = Screen(display)

    # Splash
    screen.fill(BLACK)
    screen.header("picoBird Pro")
    _splash(screen, "Starting up...", WHITE, 0)
    screen.show()

    # --- WiFi scan + connect ---
    sta = network.WLAN(network.STA_IF)
    sta.active(True)

    # If already connected to the right AP, skip scanning
    if sta.isconnected() and sta.config("ssid").startswith(AP_SSID_PREFIX):
        _splash(screen, f"Already connected", GREEN, 1)
        server_ip = _derive_server_ip(sta)
    else:
        if sta.isconnected():
            sta.disconnect()
            time.sleep(1)

        ssid = _scan_for_ap(sta, screen)
        if ssid is None:
            screen.fill(BLACK)
            screen.header("picoBird Pro")
            screen.text_center("Pi 5 not found!", 80,  RED)
            screen.text_center("Is the Pi 5 on?",  100, GRAY)
            screen.text_center(f"Looking for: {AP_SSID_PREFIX}", 120, GRAY)
            screen.text_center("Press RESET to retry", 150, GRAY)
            screen.show()
            return

        ok = _connect_wifi(sta, ssid, screen)
        if not ok:
            screen.fill(BLACK)
            screen.header("picoBird Pro")
            screen.text_center("WiFi connect failed", 80,  RED)
            screen.text_center("Press RESET to retry", 110, GRAY)
            screen.show()
            return

        server_ip = _derive_server_ip(sta)

    # --- Ping server ---
    ok = _ping_server(server_ip, screen)
    if not ok:
        _splash(screen, f"Server at {server_ip} unreachable", RED, 3)
        _splash(screen, "Is picobird-pro.service running?", GRAY, 4)
        screen.show()
        time.sleep(3)  # show the error briefly, then try the UI anyway

    # --- Launch UI ---
    _splash(screen, "Launching...", GREEN, 4)
    screen.show()
    time.sleep(0.3)

    ui = UI(
        screen=screen,
        keyboard=keyboard,
        server_host=server_ip,
        server_port=SERVER_PORT,
    )
    ui.push(HomeScreen(ui))
    ui.run()


main()
