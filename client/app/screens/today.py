"""
Today's Birds screen — your logged observations, most recent first.
Select an entry and press Enter to view the species detail.
"""
from app.screen import Screen
from lib.keyboard import PRESSED, HOLD, KEY_ESC, KEY_UP, KEY_DOWN, KEY_ENTER
from app.http import get

C_BG     = (0, 0, 0)
C_FG     = (255, 255, 255)
C_HEADER = (80, 200, 120)
C_DIM    = (100, 100, 100)
C_SEL    = (120, 255, 160)
C_ERR    = (255, 80, 80)
C_WARN   = (255, 160, 0)
C_EMPTY  = (140, 140, 140)

ROW_H   = 12
LIST_Y  = 36
VISIBLE = 21


class TodayScreen(Screen):
    def __init__(self, ui):
        super().__init__(ui)
        self._items   = []   # display strings
        self._species = []   # full dicts for opening detail
        self._sel     = 0
        self._off     = 0
        self._dirty   = True
        self._error   = ""
        self._empty_msg = ""

    def on_enter(self):
        self._dirty = True
        self._load()

    def _load(self):
        if not self.ui.connected:
            self._error = ""
            self._empty_msg = "No WiFi — cannot load observations"
            self._items = []
            self._species = []
            return

        try:
            data = get(self.ui.api_host, self.ui.api_port,
                       "/api/observations/?limit=100&offset=0", timeout=8)
            if data and isinstance(data, list) and len(data) > 0:
                self._species = data
                self._items = [
                    o.get("common_name", "?") + "  " + o.get("observed_at", "")[:10]
                    for o in data
                ]
                self._error = ""
                self._empty_msg = ""
            elif data is not None:
                self._items = []
                self._species = []
                self._error = ""
                self._empty_msg = "No sightings logged yet.\nSearch a species and press L to log!"
            else:
                self._items = []
                self._species = []
                self._error = "Server returned no data"
                self._empty_msg = ""
        except Exception as e:
            self._items = []
            self._species = []
            self._error = "Pi 5 unreachable"
            self._empty_msg = "Is picobird-pro service running?"

    def draw(self):
        if not self._dirty:
            return
        d = self.ui.display
        d.fill(*C_BG)
        d.text("My Sightings", 10, 8, fg=C_HEADER)
        count_str = "({})".format(len(self._items)) if self._items else ""
        d.text(count_str, 100, 8, fg=C_DIM)

        if self._error:
            d.text(self._error[:50], 10, LIST_Y, fg=C_ERR)
            if self._empty_msg:
                d.text(self._empty_msg[:50], 10, LIST_Y + 14, fg=C_WARN)
        elif self._empty_msg:
            # Split empty message on \n for two-line hints
            lines = self._empty_msg.split("\n")
            for i, line in enumerate(lines[:3]):
                d.text(line[:50], 10, LIST_Y + i * 14, fg=C_EMPTY)
        else:
            for i in range(VISIBLE):
                idx = self._off + i
                if idx >= len(self._items):
                    break
                y = LIST_Y + i * ROW_H
                fg = C_SEL if idx == self._sel else C_FG
                d.text(self._items[idx][:50], 10, y, fg=fg)

        d.text("Up/Dn=scroll  Enter=detail  Esc=back", 4, 306, fg=C_DIM)
        self._dirty = False

    def on_key(self, state, key):
        if state not in (PRESSED, HOLD):
            return
        if key == KEY_ESC and state == PRESSED:
            self.ui.stack.pop()
        elif key == KEY_ENTER and state == PRESSED and self._species:
            from app.screens.species_detail import SpeciesDetailScreen
            self.ui.stack.push(SpeciesDetailScreen(self.ui, self._species[self._sel]))
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
