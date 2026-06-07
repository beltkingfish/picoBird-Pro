"""
Today's Birds screen — recent eBird observations near the Pi 5.
"""
from app.screen import Screen
from lib.keyboard import PRESSED, HOLD, KEY_ESC, KEY_UP, KEY_DOWN
from app.http import get

C_BG     = (0, 0, 0)
C_FG     = (255, 255, 255)
C_HEADER = (80, 200, 120)
C_DIM    = (100, 100, 100)
C_SEL    = (120, 255, 160)
C_ERR    = (255, 80, 80)

ROW_H   = 12
LIST_Y  = 36
VISIBLE = 21  # rows that fit below header


class TodayScreen(Screen):
    def __init__(self, ui):
        super().__init__(ui)
        self._items = []
        self._sel   = 0
        self._off   = 0
        self._dirty = True
        self._error = ""

    def on_enter(self):
        self._dirty = True
        self._load()

    def _load(self):
        try:
            data = get(self.ui.api_host, self.ui.api_port, "/api/obs/recent?max=100", timeout=8)
            if data and isinstance(data, list):
                self._items = [o.get("comName", "?") + " — " + o.get("locName", "") for o in data]
                self._error = ""
            else:
                self._items = []
                self._error = "No observations returned"
        except Exception as e:
            self._items = []
            self._error = str(e)

    def draw(self):
        if not self._dirty:
            return
        d = self.ui.display
        d.fill(*C_BG)
        d.text("Today's Birds", 10, 8, fg=C_HEADER)
        if self._error:
            d.text(self._error[:50], 10, LIST_Y, fg=C_ERR)
        else:
            for i in range(VISIBLE):
                idx = self._off + i
                if idx >= len(self._items):
                    break
                y = LIST_Y + i * ROW_H
                fg = C_SEL if idx == self._sel else C_FG
                d.text(self._items[idx][:50], 10, y, fg=fg)
        d.text("Up/Dn=scroll  Esc=back", 10, 300, fg=C_DIM)
        self._dirty = False

    def on_key(self, state, key):
        if state not in (PRESSED, HOLD):
            return
        if key == KEY_ESC and state == PRESSED:
            self.ui.stack.pop()
        elif key == KEY_UP and self._sel > 0:
            self._sel -= 1
            if self._sel < self._off:
                self._off = self._sel
            self._dirty = True
        elif key == KEY_DOWN and self._sel < len(self._items) - 1:
            self._sel += 1
            if self._sel >= self._off + VISIBLE:
                self._off = self._sel - VISIBLE + 1
            self._dirty = True
