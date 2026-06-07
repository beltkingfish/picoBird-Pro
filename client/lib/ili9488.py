"""
ILI9488 driver for PicoCalc (ClockworkPi).
Hardware: SPI1, sck=10, mosi=11, cs=13, dc=14, rst=15, bl=12 (PWM)
Color: RGB666 (18-bit, 3 bytes per pixel in B,G,R order)
"""
import machine
import time

# Commands
_SWRESET  = 0x01
_SLPOUT   = 0x11
_INVON    = 0x21  # required on PicoCalc
_DISPON   = 0x29
_CASET    = 0x2A
_PASET    = 0x2B
_RAMWR    = 0x2C
_MADCTL   = 0x36
_COLMOD   = 0x3A
_PGAMCTRL = 0xE0
_NGAMCTRL = 0xE1
_ADJCTRL3 = 0xF7

WIDTH  = 320
HEIGHT = 320

# Pre-built 5×8 font (ASCII 32-126), stored as column bytes
_FONT5X8 = (
    b'\x00\x00\x00\x00\x00',  # 32 space
    b'\x00\x00\x5f\x00\x00',  # 33 !
    b'\x00\x07\x00\x07\x00',  # 34 "
    b'\x14\x7f\x14\x7f\x14',  # 35 #
    b'\x24\x2a\x7f\x2a\x12',  # 36 $
    b'\x23\x13\x08\x64\x62',  # 37 %
    b'\x36\x49\x55\x22\x50',  # 38 &
    b'\x00\x05\x03\x00\x00',  # 39 '
    b'\x00\x1c\x22\x41\x00',  # 40 (
    b'\x00\x41\x22\x1c\x00',  # 41 )
    b'\x14\x08\x3e\x08\x14',  # 42 *
    b'\x08\x08\x3e\x08\x08',  # 43 +
    b'\x00\x50\x30\x00\x00',  # 44 ,
    b'\x08\x08\x08\x08\x08',  # 45 -
    b'\x00\x60\x60\x00\x00',  # 46 .
    b'\x20\x10\x08\x04\x02',  # 47 /
    b'\x3e\x51\x49\x45\x3e',  # 48 0
    b'\x00\x42\x7f\x40\x00',  # 49 1
    b'\x42\x61\x51\x49\x46',  # 50 2
    b'\x21\x41\x45\x4b\x31',  # 51 3
    b'\x18\x14\x12\x7f\x10',  # 52 4
    b'\x27\x45\x45\x45\x39',  # 53 5
    b'\x3c\x4a\x49\x49\x30',  # 54 6
    b'\x01\x71\x09\x05\x03',  # 55 7
    b'\x36\x49\x49\x49\x36',  # 56 8
    b'\x06\x49\x49\x29\x1e',  # 57 9
    b'\x00\x36\x36\x00\x00',  # 58 :
    b'\x00\x56\x36\x00\x00',  # 59 ;
    b'\x08\x14\x22\x41\x00',  # 60 <
    b'\x14\x14\x14\x14\x14',  # 61 =
    b'\x00\x41\x22\x14\x08',  # 62 >
    b'\x02\x01\x51\x09\x06',  # 63 ?
    b'\x32\x49\x79\x41\x3e',  # 64 @
    b'\x7e\x11\x11\x11\x7e',  # 65 A
    b'\x7f\x49\x49\x49\x36',  # 66 B
    b'\x3e\x41\x41\x41\x22',  # 67 C
    b'\x7f\x41\x41\x22\x1c',  # 68 D
    b'\x7f\x49\x49\x49\x41',  # 69 E
    b'\x7f\x09\x09\x09\x01',  # 70 F
    b'\x3e\x41\x49\x49\x7a',  # 71 G
    b'\x7f\x08\x08\x08\x7f',  # 72 H
    b'\x00\x41\x7f\x41\x00',  # 73 I
    b'\x20\x40\x41\x3f\x01',  # 74 J
    b'\x7f\x08\x14\x22\x41',  # 75 K
    b'\x7f\x40\x40\x40\x40',  # 76 L
    b'\x7f\x02\x0c\x02\x7f',  # 77 M
    b'\x7f\x04\x08\x10\x7f',  # 78 N
    b'\x3e\x41\x41\x41\x3e',  # 79 O
    b'\x7f\x09\x09\x09\x06',  # 80 P
    b'\x3e\x41\x51\x21\x5e',  # 81 Q
    b'\x7f\x09\x19\x29\x46',  # 82 R
    b'\x46\x49\x49\x49\x31',  # 83 S
    b'\x01\x01\x7f\x01\x01',  # 84 T
    b'\x3f\x40\x40\x40\x3f',  # 85 U
    b'\x1f\x20\x40\x20\x1f',  # 86 V
    b'\x3f\x40\x38\x40\x3f',  # 87 W
    b'\x63\x14\x08\x14\x63',  # 88 X
    b'\x07\x08\x70\x08\x07',  # 89 Y
    b'\x61\x51\x49\x45\x43',  # 90 Z
    b'\x00\x7f\x41\x41\x00',  # 91 [
    b'\x02\x04\x08\x10\x20',  # 92 \
    b'\x00\x41\x41\x7f\x00',  # 93 ]
    b'\x04\x02\x01\x02\x04',  # 94 ^
    b'\x40\x40\x40\x40\x40',  # 95 _
    b'\x00\x01\x02\x04\x00',  # 96 `
    b'\x20\x54\x54\x54\x78',  # 97 a
    b'\x7f\x48\x44\x44\x38',  # 98 b
    b'\x38\x44\x44\x44\x20',  # 99 c
    b'\x38\x44\x44\x48\x7f',  # 100 d
    b'\x38\x54\x54\x54\x18',  # 101 e
    b'\x08\x7e\x09\x01\x02',  # 102 f
    b'\x0c\x52\x52\x52\x3e',  # 103 g
    b'\x7f\x08\x04\x04\x78',  # 104 h
    b'\x00\x44\x7d\x40\x00',  # 105 i
    b'\x20\x40\x44\x3d\x00',  # 106 j
    b'\x7f\x10\x28\x44\x00',  # 107 k
    b'\x00\x41\x7f\x40\x00',  # 108 l
    b'\x7c\x04\x18\x04\x78',  # 109 m
    b'\x7c\x08\x04\x04\x78',  # 110 n
    b'\x38\x44\x44\x44\x38',  # 111 o
    b'\x7c\x14\x14\x14\x08',  # 112 p
    b'\x08\x14\x14\x18\x7c',  # 113 q
    b'\x7c\x08\x04\x04\x08',  # 114 r
    b'\x48\x54\x54\x54\x20',  # 115 s
    b'\x04\x3f\x44\x40\x20',  # 116 t
    b'\x3c\x40\x40\x20\x7c',  # 117 u
    b'\x1c\x20\x40\x20\x1c',  # 118 v
    b'\x3c\x40\x30\x40\x3c',  # 119 w
    b'\x44\x28\x10\x28\x44',  # 120 x
    b'\x0c\x50\x50\x50\x3c',  # 121 y
    b'\x44\x64\x54\x4c\x44',  # 122 z
    b'\x00\x08\x36\x41\x00',  # 123 {
    b'\x00\x00\x7f\x00\x00',  # 124 |
    b'\x00\x41\x36\x08\x00',  # 125 }
    b'\x10\x08\x08\x10\x08',  # 126 ~
)

CHAR_W = 5
CHAR_H = 8

# Glyph cache: keyed by (char, fg_rgb666, bg_rgb666) -> 120-byte BGR666 buffer.
# Capped so a wide range of color combinations can't slowly exhaust the heap.
_glyph_cache = {}
_GLYPH_CACHE_MAX = 256


def _rgb_to_bgr666(r, g, b):
    """Pack (r,g,b) 0-255 into 3 bytes (B,G,R) each left-shifted to 6-bit."""
    return bytes([b & 0xFC, g & 0xFC, r & 0xFC])


def _make_glyph(char, fg, bg):
    """Build a 5×8 pixel BGR666 buffer (120 bytes) for a character."""
    key = (char, fg, bg)
    if key in _glyph_cache:
        return _glyph_cache[key]
    idx = ord(char) - 32
    if idx < 0 or idx >= len(_FONT5X8):
        idx = 0
    cols = _FONT5X8[idx]
    buf = bytearray(CHAR_W * CHAR_H * 3)
    off = 0
    for row in range(CHAR_H):
        for col in range(CHAR_W):
            pixel = fg if (cols[col] >> row) & 1 else bg
            buf[off:off+3] = pixel
            off += 3
    # Bound cache growth: if full, drop everything and start fresh. Crude but
    # cheap, and the working set re-populates within a frame or two.
    if len(_glyph_cache) >= _GLYPH_CACHE_MAX:
        _glyph_cache.clear()
    _glyph_cache[key] = bytes(buf)
    return _glyph_cache[key]


class ILI9488:
    def __init__(self):
        self._spi = machine.SPI(
            1,
            baudrate=62_500_000,
            polarity=0,
            phase=0,
            sck=machine.Pin(10),
            mosi=machine.Pin(11),
        )
        self._cs  = machine.Pin(13, machine.Pin.OUT, value=1)
        self._dc  = machine.Pin(14, machine.Pin.OUT, value=0)
        self._rst = machine.Pin(15, machine.Pin.OUT, value=1)
        self._bl  = machine.PWM(machine.Pin(12))
        self._bl.freq(1000)
        self._bl.duty_u16(0)
        self._init()
        self._bl.duty_u16(32768)  # 50% brightness

    def _cmd(self, cmd):
        self._dc.value(0)
        self._cs.value(0)
        self._spi.write(bytes([cmd]))
        self._cs.value(1)

    def _data(self, data):
        self._dc.value(1)
        self._cs.value(0)
        self._spi.write(data if isinstance(data, (bytes, bytearray)) else bytes([data]))
        self._cs.value(1)

    def _init(self):
        # Hard reset
        self._rst.value(0)
        time.sleep_ms(10)
        self._rst.value(1)
        time.sleep_ms(120)

        self._cmd(_SWRESET)
        time.sleep_ms(120)
        self._cmd(_SLPOUT)
        time.sleep_ms(120)

        # Positive gamma
        self._cmd(_PGAMCTRL)
        self._data(bytes([0x00,0x03,0x09,0x08,0x16,0x0a,0x3f,0x78,
                          0x4c,0x09,0x0a,0x08,0x16,0x1a,0x0f]))
        # Negative gamma
        self._cmd(_NGAMCTRL)
        self._data(bytes([0x00,0x16,0x19,0x03,0x0f,0x05,0x32,0x45,
                          0x46,0x04,0x0e,0x0d,0x35,0x37,0x0f]))

        self._cmd(_COLMOD)
        self._data(0x66)  # 18-bit RGB666

        self._cmd(_MADCTL)
        self._data(0x48)  # MX | BGR

        self._cmd(_INVON)  # required on PicoCalc

        self._cmd(_ADJCTRL3)
        self._data(bytes([0xA9, 0x51, 0x2C, 0x82]))

        self._cmd(_DISPON)
        time.sleep_ms(20)

    def _set_window(self, x0, y0, x1, y1):
        self._cmd(_CASET)
        self._data(bytes([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF]))
        self._cmd(_PASET)
        self._data(bytes([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF]))
        self._cmd(_RAMWR)

    def fill(self, r, g, b):
        """Fill screen with a solid color."""
        pixel = _rgb_to_bgr666(r, g, b)
        self._set_window(0, 0, WIDTH - 1, HEIGHT - 1)
        self._dc.value(1)
        self._cs.value(0)
        chunk = pixel * 64
        total = WIDTH * HEIGHT
        written = 0
        while written < total:
            n = min(64, total - written)
            self._spi.write(chunk[:n * 3])
            written += n
        self._cs.value(1)

    def fill_rect(self, x, y, w, h, r, g, b):
        pixel = _rgb_to_bgr666(r, g, b)
        self._set_window(x, y, x + w - 1, y + h - 1)
        self._dc.value(1)
        self._cs.value(0)
        chunk = pixel * 64
        total = w * h
        written = 0
        while written < total:
            n = min(64, total - written)
            self._spi.write(chunk[:n * 3])
            written += n
        self._cs.value(1)

    def pixel(self, x, y, r, g, b):
        self._set_window(x, y, x, y)
        self._data(_rgb_to_bgr666(r, g, b))

    def text(self, s, x, y, fg=(255, 255, 255), bg=(0, 0, 0)):
        """Draw a string using the 5×8 bitmap font."""
        fg_bytes = _rgb_to_bgr666(*fg)
        bg_bytes = _rgb_to_bgr666(*bg)
        cx = x
        for ch in s:
            if cx + CHAR_W > WIDTH:
                break
            glyph = _make_glyph(ch, fg_bytes, bg_bytes)
            self._set_window(cx, y, cx + CHAR_W - 1, y + CHAR_H - 1)
            self._data(glyph)
            cx += CHAR_W + 1

    def backlight(self, pct):
        """Set backlight brightness 0-100."""
        self._bl.duty_u16(int(pct / 100 * 65535))
