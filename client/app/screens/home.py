"""
Home screen — main menu with Today / Search / Life List / Settings.
"""
import time
from app.screen import Screen
from lib.keyboard import PRESSED, HOLD, KEY_UP, KEY_DOWN, KEY_ENTER, KEY_ESC
from app.http import get

MENU_ITEMS = ["Today's Birds", "Search Species", "My Life List", "Sound ID", "Settings"]

C_BG      = (0, 0, 0)
C_FG      = (255, 255, 255)
C_SEL_BG  = (30, 90, 50)
C_SEL_FG  = (120, 255, 160)
C_HEADER  = (80, 200, 120)
C_DIM     = (100, 100, 100)
C_ERR     = (255, 80, 80)

ROW_H = 22
START_Y = 60


class HomeScreen(Screen):
    def __init__(self, ui):
        super().__init__(ui)
        self._sel = 0
        self._dirty = True
        self._status = ""
        self._status_color = C_DIM
        self._last_ping = 0

    def on_enter(self):
        self._dirty = True
        self._ping()

    def _ping(self):
        if not self.ui.connected:
            self._status = "No WiFi - offline mode"
            self._status_color = (255, 160, 0)
            return
        try:
            r = get(self.ui.api_host, self.ui.api_port, "/api/ping", timeout=3)
            if r and r.get("status") == "ok":
                self._status = "Pi 5 connected"
                self._status_color = (80, 200, 120)
            else:
                self._status = "Pi 5 unreachable"
                self._status_color = (255, 160, 0)
        except Exception:
            self._status = "Pi 5 unreachable"
            self._status_color = (255, 160, 0)

    def draw(self):
        if not self._dirty:
            now = time.ticks_ms()
            if time.ticks_diff(now, self._last_ping) > 30_000:
                self._last_ping = now
                old = self._status
                self._ping()
                if self._status != old:
                    self._dirty = True
            return

        d = self.ui.display
        d.fill(*C_BG)

        d.text("picoBird Pro", 10, 8, fg=C_HEADER)
        d.text(self._status, 10, 22, fg=self._status_color)
        d.fill_rect(0, 42, 320, 1, 40, 100, 60)

        for i, item in enumerate(MENU_ITEMS):
            y = START_Y + i * ROW_H
            if i == self._sel:
                d.fill_rect(0, y - 2, 320, ROW_H, *C_SEL_BG)
                d.text("> " + item, 10, y, fg=C_SEL_FG)
            else:
                d.text("  " + item, 10, y, fg=C_FG)

        d.text("Joy/arrows=nav  Center/Enter=open", 4, 300, fg=C_DIM)

        self._dirty = False
        self._last_ping = time.ticks_ms()

    def on_key(self, state, key):
        # Accept both PRESSED and HOLD for smooth navigation
        if state not in (PRESSED, HOLD):
            return
        if key == KEY_UP:
            self._sel = (self._sel - 1) % len(MENU_ITEMS)
            self._dirty = True
        elif key == KEY_DOWN:
            self._sel = (self._sel + 1) % len(MENU_ITEMS)
            self._dirty = True
        elif key == KEY_ENTER and state == PRESSED:
            self._open_selected()

    def _open_selected(self):
        from app.screens.today import TodayScreen
        from app.screens.search import SearchScreen
        from app.screens.lifelist import LifeListScreen

        if self._sel == 0:
            self.ui.stack.push(TodayScreen(self.ui))
        elif self._sel == 1:
            self.ui.stack.push(SearchScreen(self.ui))
        elif self._sel == 2:
            self.ui.stack.push(LifeListScreen(self.ui))
        else:
            self._status = MENU_ITEMS[self._sel] + ": coming soon"
            self._status_color = (180, 180, 50)
            self._dirty = True
