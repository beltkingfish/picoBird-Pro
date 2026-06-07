"""
Species search screen — type to search the local taxonomy database.
"""
from app.screen import Screen
from lib.keyboard import PRESSED, KEY_ESC, KEY_UP, KEY_DOWN, KEY_ENTER, KEY_BACKSPACE
from app.http import get

C_BG     = (0, 0, 0)
C_FG     = (255, 255, 255)
C_HEADER = (80, 200, 120)
C_DIM    = (100, 100, 100)
C_SEL    = (120, 255, 160)
C_CURSOR = (255, 255, 0)

ROW_H   = 12
LIST_Y  = 50
VISIBLE = 20


class SearchScreen(Screen):
    def __init__(self, ui):
        super().__init__(ui)
        self._query  = ""
        self._items  = []
        self._sel    = 0
        self._off    = 0
        self._dirty  = True

    def on_enter(self):
        self._dirty = True

    def _search(self):
        if not self._query:
            self._items = []
            return
        try:
            path = "/api/species/search?q=" + self._query.replace(" ", "+") + "&limit=80"
            data = get(self.ui.api_host, self.ui.api_port, path, timeout=5)
            if data and isinstance(data, list):
                self._items = [s.get("comName", "?") for s in data]
            else:
                self._items = []
        except Exception:
            self._items = []
        self._sel = 0
        self._off = 0

    def draw(self):
        if not self._dirty:
            return
        d = self.ui.display
        d.fill(*C_BG)
        d.text("Search Species", 10, 8, fg=C_HEADER)
        # Query box
        display_q = self._query[-36:] if len(self._query) > 36 else self._query
        d.text(">" + display_q + "_", 10, 26, fg=C_CURSOR)

        for i in range(VISIBLE):
            idx = self._off + i
            if idx >= len(self._items):
                break
            fg = C_SEL if idx == self._sel else C_FG
            d.text(self._items[idx][:50], 10, LIST_Y + i * ROW_H, fg=fg)

        d.text("Type=search  Esc=back", 10, 300, fg=C_DIM)
        self._dirty = False

    def on_key(self, state, key):
        if state != PRESSED:
            return
        if key == KEY_ESC:
            self.ui.stack.pop()
        elif key == KEY_BACKSPACE:
            self._query = self._query[:-1]
            self._search()
            self._dirty = True
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
        elif 0x20 <= key <= 0x7E:
            self._query += chr(key)
            self._search()
            self._dirty = True
