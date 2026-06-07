"""
picoBird Pro — PicoCalc client entry point.
Connects to Pi 5 AP (picoBirdPro / 192.168.4.1:5000) via WiFi.
"""
import time
import network
import machine

from lib.ili9488 import ILI9488
from lib.keyboard import Keyboard, PRESSED, KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_ENTER, KEY_ESC
from app.ui import UI

# ── Hardware pins (PicoCalc / ClockworkPi) ──────────────────────────────────
# Display: SPI1
#   SCK=10  MOSI=11  CS=13  DC=14  RST=15  BL=12 (PWM)
# Keyboard: I2C1
#   SDA=6   SCL=7   addr=0x1F
# (pin constants are set inside ili9488.py and keyboard.py)

# ── Network config ───────────────────────────────────────────────────────────
AP_SSID     = "picoBirdPro"
AP_PASSWORD = "picoBird1"
API_HOST    = "192.168.4.1"
API_PORT    = 5000

CONNECT_TIMEOUT = 20  # seconds


def connect_wifi(display):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    display.fill(0, 0, 0)
    display.text("picoBird Pro", 10, 10, fg=(80, 200, 120))
    display.text("Scanning for Pi 5...", 10, 30)

    deadline = time.ticks_add(time.ticks_ms(), CONNECT_TIMEOUT * 1000)
    if not wlan.isconnected():
        wlan.connect(AP_SSID, AP_PASSWORD)
        while not wlan.isconnected():
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                display.text("WiFi timeout.", 10, 50, fg=(255, 80, 80))
                return None
            display.text(".", 10 + (CONNECT_TIMEOUT - time.ticks_diff(deadline, time.ticks_ms()) // 1000) * 6, 50)
            time.sleep_ms(500)

    ip = wlan.ifconfig()[0]
    display.text("Connected: " + ip, 10, 50, fg=(80, 255, 80))
    time.sleep_ms(800)
    return wlan


def main():
    display = ILI9488()
    kb      = Keyboard()
    wlan    = connect_wifi(display)

    ui = UI(display, kb, API_HOST, API_PORT, connected=(wlan is not None))
    ui.run()


main()
