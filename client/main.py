"""picoBird Pro — PicoCalc client boot sequence."""

import time
import network
from machine import SPI, Pin, I2C

from lib.ili9488 import ILI9488
from lib.keyboard import Keyboard
from app.screen import Screen
from app.ui import UI
from app.screens.home import HomeScreen

# ---------------------------------------------------------------------------
# Hardware constants — adjust to match your wiring
# ---------------------------------------------------------------------------
SPI_ID   = 0
SPI_MOSI = 3
SPI_SCK  = 2
SPI_MISO = 4
DISP_CS  = 5
DISP_DC  = 6
DISP_RST = 7
DISP_BL  = 8

KBD_SDA  = 20
KBD_SCL  = 21
KBD_I2C  = 0

SERVER_SSID = "picoBirdPro"
SERVER_PASS = "fieldguide"
SERVER_HOST = "192.168.4.1"
SERVER_PORT = 5000


def connect_wifi(ssid: str, password: str, timeout_s: int = 15) -> bool:
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if sta.isconnected():
        return True
    sta.connect(ssid, password)
    deadline = time.time() + timeout_s
    while not sta.isconnected():
        if time.time() > deadline:
            return False
        time.sleep(0.5)
    return True


def main():
    # --- Display ---
    spi = SPI(
        SPI_ID,
        baudrate=40_000_000,
        polarity=0,
        phase=0,
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
        width=320,
        height=320,
    )

    # --- Keyboard ---
    i2c = I2C(KBD_I2C, sda=Pin(KBD_SDA), scl=Pin(KBD_SCL), freq=100_000)
    keyboard = Keyboard(i2c)

    # --- Screen helper ---
    screen = Screen(display)
    screen.fill(0x0000)
    screen.text("picoBird Pro", 80, 10, 0xFFFF)
    screen.text("Connecting to Pi 5...", 20, 30, 0xAD75)
    screen.show()

    # --- WiFi ---
    ok = connect_wifi(SERVER_SSID, SERVER_PASS)
    if not ok:
        screen.fill(0x0000)
        screen.text("WiFi failed!", 80, 140, 0xF800)
        screen.text("Check Pi 5 is on.", 50, 160, 0xFFFF)
        screen.show()
        return

    # --- Launch UI ---
    ui = UI(
        screen=screen,
        keyboard=keyboard,
        server_host=SERVER_HOST,
        server_port=SERVER_PORT,
    )
    ui.push(HomeScreen(ui))
    ui.run()


main()
