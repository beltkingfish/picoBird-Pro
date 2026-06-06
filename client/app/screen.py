"""Screen helper — thin wrapper around ILI9488 with text/layout utilities."""

from lib.ili9488 import ILI9488

# RGB565 palette
BLACK   = 0x0000
WHITE   = 0xFFFF
GREEN   = 0x07E0
RED     = 0xF800
BLUE    = 0x001F
YELLOW  = 0xFFE0
CYAN    = 0x07FF
GRAY    = 0x7BEF
DARKGRY = 0x39E7
ACCENT  = 0x05FF  # teal-ish

CHAR_W  = 8
CHAR_H  = 8


class Screen:
    def __init__(self, display: ILI9488):
        self.d      = display
        self.width  = display.width
        self.height = display.height
        self.cols   = display.width  // CHAR_W
        self.rows   = display.height // CHAR_H

    # Delegate draw primitives
    def fill(self, color: int = BLACK):        self.d.fill(color)
    def pixel(self, x, y, c):                 self.d.pixel(x, y, c)
    def hline(self, x, y, w, c):              self.d.hline(x, y, w, c)
    def vline(self, x, y, h, c):              self.d.vline(x, y, h, c)
    def rect(self, x, y, w, h, c):            self.d.rect(x, y, w, h, c)
    def fill_rect(self, x, y, w, h, c):       self.d.fill_rect(x, y, w, h, c)
    def show(self):                            self.d.show()

    def text(self, s: str, x: int, y: int,
             fg: int = WHITE, bg: int = BLACK, scale: int = 1):
        self.d.text(s, x, y, fg, bg, scale)

    def text_center(self, s: str, y: int, fg: int = WHITE, bg: int = BLACK):
        x = (self.width - len(s) * CHAR_W) // 2
        self.text(s, max(0, x), y, fg, bg)

    def clear_row(self, row: int, bg: int = BLACK):
        self.fill_rect(0, row * CHAR_H, self.width, CHAR_H, bg)

    def header(self, title: str, fg: int = WHITE, bg: int = ACCENT):
        """Draw a full-width title bar at the top."""
        self.fill_rect(0, 0, self.width, CHAR_H + 4, bg)
        self.text_center(title, 2, fg, bg)

    def status_bar(self, msg: str, fg: int = WHITE, bg: int = DARKGRY):
        """Draw a status bar at the bottom."""
        y = self.height - CHAR_H - 4
        self.fill_rect(0, y, self.width, CHAR_H + 4, bg)
        self.text(msg[:self.cols], 2, y + 2, fg, bg)

    def wrap_text(self, s: str, x: int, y: int, max_width: int,
                  fg: int = WHITE, bg: int = BLACK) -> int:
        """Render word-wrapped text. Returns the Y position after the last line."""
        words = s.split()
        line  = ""
        chars_per_row = max_width // CHAR_W
        cy = y
        for word in words:
            if len(line) + len(word) + 1 <= chars_per_row:
                line = f"{line} {word}".strip()
            else:
                if line:
                    self.text(line, x, cy, fg, bg)
                    cy += CHAR_H
                line = word
        if line:
            self.text(line, x, cy, fg, bg)
            cy += CHAR_H
        return cy
