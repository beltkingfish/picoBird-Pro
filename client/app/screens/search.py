"""
Species search screen — type to search the local taxonomy database.
Selecting a result opens the species detail screen.
"""
from app.screen import Screen
from lib.keyboard import PRESSED, HOLD, KEY_ESC, KEY_UP, KEY_DOWN, KEY_ENTER, KEY_BACKSPACE
from app.http import get, quote, as_list

MAX_QUERY = 50  # cap query length to keep URLs and RAM sane

from app import theme as T

C_BG     = T.C_BG
C_FG     = T.C_FG
C_HEADER = T.C_HEADER
C_DIM    = T.C_DIM
C_SEL    = T.C_SEL
C_CURSOR = T.C_CURSOR

ROW_H   = 12
LIST_Y  = 50
VISIBLE = 20


class SearchScreen(Screen):
    def __init__(self, ui):
        super().__init__(ui)
        self._query   = ""
        self._species = []   # full dicts from API
        self._sel     = 0
        self._off     = 0
        self._dirty   = True

    def on_enter(self):
        self._dirty = True

    def _search(self):
        if not self._query:
            self._species = []
            return
        try:
            path = "/api/species/search?q=" + quote(self._query) + "&page=0"
            data = get(self.ui.api_host, self.ui.api_port, path, timeout=5)
            self._species = as_list(data)
        except Exception:
            self._species = []
        self._sel = 0
        self._off = 0

    def draw(self):
        if not self._dirty:
            return
        d = self.ui.display
        d.fill(*C_BG)
        d.text("Search Species", 10, 8, fg=C_HEADER)
        display_q = self._query[-36:] if len(self._query) > 36 else self._query
        d.text(">" + display_q + "_", 10, 26, fg=C_CURSOR)

        for i in range(VISIBLE):
            idx = self._off + i
            if idx >= len(self._species):
                break
            fg = C_SEL if idx == self._sel else C_FG
            name = self._species[idx].get("common_name", self._species[idx].get("comName", "?"))
            d.text(name[:50], 10, LIST_Y + i * ROW_H, fg=fg)

        hint = "Type=search  Enter=detail  Esc=back"
        d.text(hint, 4, 300, fg=C_DIM)
        self._dirty = False

    def on_key(self, state, key):
        if state not in (PRESSED, HOLD):
            return
        if key == KEY_ESC and state == PRESSED:
            self.ui.stack.pop()
        elif key == KEY_ENTER and state == PRESSED and self._species:
            from app.screens.species_detail import SpeciesDetailScreen
            self.ui.stack.push(SpeciesDetailScreen(self.ui, self._species[self._sel]))
        elif key == KEY_BACKSPACE:
            self._query = self._query[:-1]
            self._search()
            self._dirty = True
        elif key == KEY_UP and self._sel > 0:
            self._sel -= 1
            if self._sel < self._off:
                self._off = self._sel
            self._dirty = True
        elif key == KEY_DOWN and self._sel < len(self._species) - 1:
            self._sel += 1
            if self._sel >= self._off + VISIBLE:
                self._off = self._sel - VISIBLE + 1
            self._dirty = True
        elif 0x20 <= key <= 0x7E and state == PRESSED:
            if len(self._query) < MAX_QUERY:
                self._query += chr(key)
                self._search()
                self._dirty = True
