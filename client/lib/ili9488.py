"""ILI9488 SPI display driver for MicroPython (320×320 PicoCalc panel)."""

import time
from micropython import const

_NOP       = const(0x00)
_SWRESET   = const(0x01)
_SLPOUT    = const(0x11)
_NORON     = const(0x13)
_INVOFF    = const(0x20)
_DISPON    = const(0x29)
_CASET     = const(0x2A)
_PASET     = const(0x2B)
_RAMWR     = const(0x2C)
_MADCTL    = const(0x36)
_COLMOD    = const(0x3A)
_PGAMCTRL  = const(0xE0)
_NGAMCTRL  = const(0xE1)
_IFMODE    = const(0xB0)
_FRMCTR1   = const(0xB1)
_DISCTRL   = const(0xB6)
_PWCTRL1   = const(0xC0)
_PWCTRL2   = const(0xC1)
_VMCTRL1   = const(0xC5)

_MADCTL_MX  = const(0x40)
_MADCTL_BGR = const(0x08)


class ILI9488:
    """Minimal ILI9488 driver.  Pixel data is 16-bit RGB565."""

    def __init__(self, spi, cs, dc, rst, bl=None,
                 width: int = 320, height: int = 320):
        self.spi    = spi
        self.cs     = cs
        self.dc     = dc
        self.rst    = rst
        self.bl     = bl
        self.width  = width
        self.height = height
        self._buf   = bytearray(width * height * 2)
        self._init()

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    def _cmd(self, cmd: int):
        self.dc.value(0)
        self.cs.value(0)
        self.spi.write(bytes([cmd]))
        self.cs.value(1)

    def _data(self, data):
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(data if isinstance(data, (bytes, bytearray)) else bytes(data))
        self.cs.value(1)

    def _write(self, cmd: int, data=None):
        self._cmd(cmd)
        if data:
            self._data(data)

    def _init(self):
        # Hard reset
        self.rst.value(0)
        time.sleep_ms(10)
        self.rst.value(1)
        time.sleep_ms(120)

        self._write(_SWRESET)
        time.sleep_ms(150)
        self._write(_SLPOUT)
        time.sleep_ms(50)

        self._write(_COLMOD,   b'\x55')           # 16-bit RGB565
        self._write(_MADCTL,   bytes([_MADCTL_MX | _MADCTL_BGR]))
        self._write(_PWCTRL1,  b'\x17\x15')
        self._write(_PWCTRL2,  b'\x41')
        self._write(_VMCTRL1,  b'\x00\x12\x80')
        self._write(_FRMCTR1,  b'\xA0')
        self._write(_DISCTRL,  b'\x02\x02')
        self._write(_NORON)
        time.sleep_ms(10)
        self._write(_DISPON)
        time.sleep_ms(50)

        if self.bl:
            self.bl.value(1)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _set_window(self, x0: int, y0: int, x1: int, y1: int):
        self._write(_CASET, bytes([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF]))
        self._write(_PASET, bytes([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF]))
        self._cmd(_RAMWR)

    def fill(self, color: int):
        """Fill the entire framebuffer with a RGB565 color."""
        hi = (color >> 8) & 0xFF
        lo = color & 0xFF
        mv = memoryview(self._buf)
        for i in range(0, len(mv), 2):
            mv[i]   = hi
            mv[i+1] = lo

    def pixel(self, x: int, y: int, color: int):
        idx = (y * self.width + x) * 2
        self._buf[idx]   = (color >> 8) & 0xFF
        self._buf[idx+1] = color & 0xFF

    def hline(self, x: int, y: int, w: int, color: int):
        hi = (color >> 8) & 0xFF
        lo = color & 0xFF
        base = (y * self.width + x) * 2
        for i in range(w):
            self._buf[base + i*2]   = hi
            self._buf[base + i*2+1] = lo

    def vline(self, x: int, y: int, h: int, color: int):
        hi = (color >> 8) & 0xFF
        lo = color & 0xFF
        for row in range(h):
            base = ((y + row) * self.width + x) * 2
            self._buf[base]   = hi
            self._buf[base+1] = lo

    def rect(self, x: int, y: int, w: int, h: int, color: int):
        self.hline(x, y,         w, color)
        self.hline(x, y + h - 1, w, color)
        self.vline(x,         y, h, color)
        self.vline(x + w - 1, y, h, color)

    def fill_rect(self, x: int, y: int, w: int, h: int, color: int):
        hi = (color >> 8) & 0xFF
        lo = color & 0xFF
        for row in range(h):
            base = ((y + row) * self.width + x) * 2
            for col in range(w):
                self._buf[base + col*2]   = hi
                self._buf[base + col*2+1] = lo

    def text(self, s: str, x: int, y: int, color: int, bg: int = 0x0000, scale: int = 1):
        """Render ASCII text using MicroPython's built-in 8×8 font."""
        import framebuf
        for ch in s:
            glyph_buf = bytearray(8)
            fb = framebuf.FrameBuffer(glyph_buf, 8, 8, framebuf.MONO_VLSB)
            fb.text(ch, 0, 0, 1)
            for row in range(8):
                for col in range(8):
                    px_color = color if (glyph_buf[col] >> row) & 1 else bg
                    if scale == 1:
                        self.pixel(x + col, y + row, px_color)
                    else:
                        self.fill_rect(x + col*scale, y + row*scale, scale, scale, px_color)
            x += 8 * scale

    def show(self):
        """Flush framebuffer to display."""
        self._set_window(0, 0, self.width - 1, self.height - 1)
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(self._buf)
        self.cs.value(1)
