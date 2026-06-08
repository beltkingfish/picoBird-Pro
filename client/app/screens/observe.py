"""
Log Sighting screen — type to search, pick a species, jump straight to logging.
A faster path than Search -> detail -> Log for "saw a bird, log it now".
"""
import time
from app.screen import Screen
from lib.keyboard import PRESSED, HOLD, KEY_ESC, KEY_UP, KEY_DOWN, KEY_ENTER, KEY_BACKSPACE
from app.http import get, quote, as_list

MAX_QUERY  = 50
DEBOUNCE_MS = 200   # wait this long after last keypress before firing search

from app import theme as T

C_BG     = T.C_BG
C_FG     = T.C_FG
C_HEADER = T.C_HEADER
C_DIM    = T.C_DIM
C_SEL    = T.C_SEL
C_CURSOR = T.C_CURSOR

ROW_H   = 12
LIST_Y  = 50
VISIBLE = 18


class ObserveScreen(Screen):
    def __init__(self, ui):
        super().__init__(ui)
        self._query          = ""
        self._species        = []
        self._sel            = 0
        self._off            = 0
        self._dirty          = True
        self._needs_full     = True
        self._last_sel       = 0
        self._search_pending = False
        self._search_at      = 0

    def on_enter(self):
        self._dirty      = True
        self._needs_full = True

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

    def _draw_result_row(self, vis_i):
        d = self.ui.display
        idx = self._off + vis_i
        y = LIST_Y + vis_i * ROW_H
        d.fill_rect(0, y - 1, 320, ROW_H, *C_BG)
        if idx >= len(self._species):
            return
        fg = C_SEL if idx == self._sel else C_FG
        name = self._species[idx].get("common_name", self._species[idx].get("comName", "?"))
        d.text(name[:50], 10, y, fg=fg)

    def draw(self):
        # Fire debounced search when timer expires.
        if self._search_pending and time.ticks_diff(time.ticks_ms(), self._search_at) >= 0:
            self._search_pending = False
            self._search()
            self._needs_full = True
            self._dirty = True

        if not self._dirty:
            return

        if not self._needs_full and self._species:
            # Selection moved within current window — repaint two rows only.
            old_vis = self._last_sel - self._off
            new_vis = self._sel - self._off
            if 0 <= old_vis < VISIBLE:
                self._draw_result_row(old_vis)
            if 0 <= new_vis < VISIBLE:
                self._draw_result_row(new_vis)
            self._last_sel = self._sel
            self._dirty = False
            return

        d = self.ui.display
        d.fill(*C_BG)
        d.text("Log Sighting", 10, 8, fg=C_HEADER)
        if self.ui.active_session:
            d.text("REC: " + (self.ui.active_session.get("name") or "")[:30], 10, 22, fg=T.C_OK)
        display_q = self._query[-36:] if len(self._query) > 36 else self._query
        d.text(">" + display_q + "_", 10, 34, fg=C_CURSOR)

        for i in range(VISIBLE):
            idx = self._off + i
            if idx >= len(self._species):
                break
            fg = C_SEL if idx == self._sel else C_FG
            name = self._species[idx].get("common_name", self._species[idx].get("comName", "?"))
            d.text(name[:50], 10, LIST_Y + i * ROW_H, fg=fg)

        d.text("Type=search  Enter=log  Esc=back", 4, 306, fg=C_DIM)
        self._last_sel   = self._sel
        self._needs_full = False
        self._dirty      = False

    def on_key(self, state, key):
        if state not in (PRESSED, HOLD):
            return
        if key == KEY_ESC and state == PRESSED:
            self.ui.stack.pop()
        elif key == KEY_ENTER and state == PRESSED and self._species:
            sp = self._species[self._sel]
            code = sp.get("species_code", sp.get("speciesCode", ""))
            name = sp.get("common_name", sp.get("comName", "Unknown"))
            from app.screens.log_sighting import LogSightingScreen
            self.ui.stack.push(LogSightingScreen(self.ui, code, name))
        elif key == KEY_BACKSPACE:
            self._query = self._query[:-1]
            self._search_pending = True
            self._search_at = time.ticks_add(time.ticks_ms(), DEBOUNCE_MS)
            self._needs_full = True
            self._dirty = True
        elif key == KEY_UP and self._sel > 0:
            self._sel -= 1
            if self._sel < self._off:
                self._off = self._sel
                self._needs_full = True
            else:
                self._needs_full = False
            self._dirty = True
        elif key == KEY_DOWN and self._sel < len(self._species) - 1:
            self._sel += 1
            if self._sel >= self._off + VISIBLE:
                self._off = self._sel - VISIBLE + 1
                self._needs_full = True
            else:
                self._needs_full = False
            self._dirty = True
        elif 0x20 <= key <= 0x7E and state == PRESSED:
            if len(self._query) < MAX_QUERY:
                self._query += chr(key)
                self._search_pending = True
                self._search_at = time.ticks_add(time.ticks_ms(), DEBOUNCE_MS)
                self._needs_full = True
                self._dirty = True
