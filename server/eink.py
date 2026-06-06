"""Waveshare 2.9" V2 e-ink display driver for Raspberry Pi (SPI).

Pinout (BCM numbering):
  VCC  -> 3.3 V
  GND  -> GND
  DIN  -> GPIO 10 (SPI0 MOSI)
  CLK  -> GPIO 11 (SPI0 SCLK)
  CS   -> GPIO  8 (SPI0 CE0)
  DC   -> GPIO 25
  RST  -> GPIO 17
  BUSY -> GPIO 24

Panel: 296 x 128 px, black/white.
"""

import time
import spidev
import RPi.GPIO as GPIO

# BCM pin numbers
PIN_DC   = 25
PIN_RST  = 17
PIN_BUSY = 24
PIN_CS   = 8

WIDTH  = 296
HEIGHT = 128

# Commands
_DRIVER_OUTPUT     = 0x01
_DEEP_SLEEP        = 0x10
_DATA_ENTRY        = 0x11
_SW_RESET          = 0x12
_TEMP_SENSOR       = 0x18
_MASTER_ACTIVATION = 0x20
_DISP_UPDATE_CTRL2 = 0x22
_WRITE_RAM_BW      = 0x24
_WRITE_VCOM        = 0x2C
_WRITE_LUT         = 0x32
_SET_DUMMY_LINE    = 0x3A
_SET_GATE_TIME     = 0x3B
_BORDER_WAVEFORM   = 0x3C
_SET_RAM_X         = 0x44
_SET_RAM_Y         = 0x45
_SET_RAM_X_ADDR    = 0x4E
_SET_RAM_Y_ADDR    = 0x4F
_NOP               = 0xFF

# Full-refresh LUT for 2.9" V2
_LUT_FULL = [
    0x80, 0x60, 0x40, 0x00, 0x00, 0x00, 0x00,
    0x10, 0x60, 0x20, 0x00, 0x00, 0x00, 0x00,
    0x80, 0x60, 0x40, 0x00, 0x00, 0x00, 0x00,
    0x10, 0x60, 0x20, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x03, 0x03, 0x00, 0x00, 0x02,
    0x09, 0x09, 0x00, 0x00, 0x02,
    0x03, 0x03, 0x00, 0x00, 0x02,
    0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00,
    0x15, 0x41, 0xA8, 0x32, 0x30, 0x0A,
]


class EPD:
    """2.9" 296x128 e-paper display."""

    def __init__(self):
        self.spi  = spidev.SpiDev()
        self.width  = WIDTH
        self.height = HEIGHT
        self._setup_gpio()
        self._setup_spi()

    def _setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(PIN_DC,   GPIO.OUT)
        GPIO.setup(PIN_RST,  GPIO.OUT)
        GPIO.setup(PIN_BUSY, GPIO.IN)

    def _setup_spi(self):
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 4_000_000
        self.spi.mode = 0

    def _cmd(self, cmd: int):
        GPIO.output(PIN_DC, GPIO.LOW)
        self.spi.writebytes([cmd])

    def _data(self, data):
        GPIO.output(PIN_DC, GPIO.HIGH)
        if isinstance(data, int):
            self.spi.writebytes([data])
        else:
            # Chunk to avoid SPI buffer limits
            for i in range(0, len(data), 4096):
                self.spi.writebytes(list(data[i:i + 4096]))

    def _wait_busy(self, timeout: float = 10.0):
        deadline = time.time() + timeout
        while GPIO.input(PIN_BUSY) == 1:  # HIGH = busy
            if time.time() > deadline:
                raise TimeoutError("e-ink BUSY timeout")
            time.sleep(0.01)

    def _reset(self):
        GPIO.output(PIN_RST, GPIO.HIGH)
        time.sleep(0.2)
        GPIO.output(PIN_RST, GPIO.LOW)
        time.sleep(0.002)
        GPIO.output(PIN_RST, GPIO.HIGH)
        time.sleep(0.2)
        self._wait_busy()

    def init(self):
        self._reset()
        self._wait_busy()
        self._cmd(_SW_RESET)
        self._wait_busy()

        self._cmd(_DRIVER_OUTPUT)
        self._data(0x27)  # (HEIGHT - 1) & 0xFF
        self._data(0x01)  # (HEIGHT - 1) >> 8
        self._data(0x00)

        self._cmd(_DATA_ENTRY)
        self._data(0x03)  # X increment, Y increment

        self._set_window(0, 0, WIDTH - 1, HEIGHT - 1)

        self._cmd(_BORDER_WAVEFORM)
        self._data(0x05)

        self._cmd(_TEMP_SENSOR)
        self._data(0x80)  # built-in temp sensor

        self._cmd(_DISP_UPDATE_CTRL2)
        self._data(0xB1)
        self._cmd(_MASTER_ACTIVATION)
        self._wait_busy()

        self._set_cursor(0, 0)

    def _set_window(self, x0, y0, x1, y1):
        self._cmd(_SET_RAM_X)
        self._data(x0 >> 3)
        self._data(x1 >> 3)
        self._cmd(_SET_RAM_Y)
        self._data(y0 & 0xFF)
        self._data(y0 >> 8)
        self._data(y1 & 0xFF)
        self._data(y1 >> 8)

    def _set_cursor(self, x, y):
        self._cmd(_SET_RAM_X_ADDR)
        self._data(x >> 3)
        self._cmd(_SET_RAM_Y_ADDR)
        self._data(y & 0xFF)
        self._data(y >> 8)

    def display(self, image_bytes: bytes):
        """Push a full 296x128 1-bit image (packed bytes, 0=black, 1=white)."""
        self._set_window(0, 0, WIDTH - 1, HEIGHT - 1)
        self._set_cursor(0, 0)
        self._cmd(_WRITE_RAM_BW)
        self._data(image_bytes)
        self._cmd(_DISP_UPDATE_CTRL2)
        self._data(0xF7)
        self._cmd(_MASTER_ACTIVATION)
        self._wait_busy()

    def clear(self, white: bool = True):
        fill = 0xFF if white else 0x00
        buf  = bytes([fill] * (WIDTH * HEIGHT // 8))
        self.display(buf)

    def sleep(self):
        self._cmd(_DEEP_SLEEP)
        self._data(0x01)

    def close(self):
        self.sleep()
        self.spi.close()
        GPIO.cleanup()
