"""
Life List screen — unique species the user has ever logged.
Shows total count in header. Offline-aware messaging.
"""
from app.screen import Screen
from lib.keyboard import PRESSED, HOLD, KEY_ESC, KEY_UP, KEY_DOWN
from app.http import get

C_BG    = (0, 0, 0)
C_FG    = (255, 255, 255)
C_HEADER = (80, 200, 120)
C_DIM   = (100, 100, 100)
C_SEL   = (120, 255, 160)
C_ERR   = (255, 80, 80)
C_WARN  = (255, 160, 0)
C_EMPTY = (140, 140, 140)

ROW_H   = 12
LIST_Y  = 36
VISIBLE = 21


class LifeListScreen(Screen):
    def __init__(self, ui):
        super().__init__(ui)
        self._items     = []
        self._sel       = 0
        self._off       = 0
        self._dirty     = True
        self._error     = ""
        self._empty_msg = ""

    def on_enter(self):
        self._dirty = True
        self._load()

    def _load(self):
        if not self.ui.connected:
            self._items = []
            self._error = ""
            self._empty_msg = "No WiFi — life list unavailable"
            return
        try:
            data = get(self.ui.api_host, self.ui.api_port, "/api/lifelist/", timeout=6)
            if data and isinstance(data, list) and len(data) > 0:
                self._items = [e.get("common_name", e.get("comName", "?")) for e in data]
                self._error = ""
                self._empty_msg = ""
            elif data is not None:
                self._items = []
                self._error = ""
                self._empty_msg = "Life list is empty.\nLog your first bird via Search!"
            else:
                self._items = []
                self._error = "Pi 5 unreachable"
                self._empty_msg = ""
        except Exception:
            self._items = []
            self._error = "Pi 5 unreachable"
            self._empty_msg = "Is picobird-pro service running?"

    def draw(self):
        if not self._dirty:
            return
        d = self.ui.display
        d.fill(*C_BG)

        count_label = "{} species".format(len(self._items)) if self._items else "0 species"
        d.text("Life List", 10, 8, fg=C_HEADER)
        d.text(count_label, 80, 8, fg=C_DIM)

        if self._error:
            d.text(self._error[:50], 10, LIST_Y, fg=C_ERR)
            if self._empty_msg:
                d.text(self._empty_msg[:50], 10, LIST_Y + 14, fg=C_WARN)
        elif self._empty_msg:
            lines = self._empty_msg.split("\n")
            for i, line in enumerate(lines[:3]):
                d.text(line[:50], 10, LIST_Y + i * 14, fg=C_EMPTY)
        else:
            for i in range(VISIBLE):
                idx = self._off + i
                if idx >= len(self._items):
                    break
                fg = C_SEL if idx == self._sel else C_FG
                d.text(self._items[idx][:50], 10, LIST_Y + i * ROW_H, fg=fg)

        d.text("Up/Dn=scroll  Esc=back", 10, 306, fg=C_DIM)
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
