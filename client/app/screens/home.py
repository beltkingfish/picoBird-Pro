"""
Home screen — main menu, connection status, and recently logged birds.
"""
import time
from app.screen import Screen
from lib.keyboard import PRESSED, HOLD, KEY_UP, KEY_DOWN, KEY_ENTER, KEY_ESC
from app.http import get, as_list

MENU_ITEMS = ["Today's Birds", "Search Species", "My Life List", "Sound ID", "Settings"]

from app import theme as T

C_BG      = T.C_BG
C_FG      = T.C_FG
C_SEL_BG  = T.C_SEL_BG
C_SEL_FG  = T.C_SEL_FG
C_HEADER  = T.C_HEADER
C_DIM     = T.C_DIM
C_WARN    = T.C_WARN
C_ERR     = T.C_ERR
C_RECENT  = T.C_RECENT

ROW_H   = 20
START_Y = 58   # menu starts here
RECENT_Y = 222 # recently seen section starts here
RECENT_MAX = 4 # number of recent birds to show


class HomeScreen(Screen):
    def __init__(self, ui):
        super().__init__(ui)
        self._sel          = 0
        self._dirty        = True
        self._status       = "Connecting..."
        self._status_color = C_DIM
        self._status2      = ""          # second status line (offline detail)
        self._status2_color = C_DIM
        self._last_ping    = 0
        self._recent       = []          # list of recent bird names

    def on_enter(self):
        self._dirty = True
        self._refresh()

    # ── Data loading ─────────────────────────────────────────────────────────

    def _refresh(self):
        """Ping server and load recent sightings."""
        self._check_connection()
        if self.ui.connected and "connected" in self._status:
            self._load_recent()

    def _check_connection(self):
        # Always re-test so the device recovers from a dropped link/server
        # without needing a reboot.
        if not self.ui.wifi_connected():
            self.ui.connected = False
            self._status  = "No WiFi"
            self._status_color = C_ERR
            self._status2 = "Offline - search unavailable"
            self._status2_color = C_WARN
            return

        try:
            r = get(self.ui.api_host, self.ui.api_port, "/api/ping", timeout=3)
            if r and r.get("status") == "ok":
                self.ui.connected = True
                self._status  = "Pi 5 connected"
                self._status_color = C_HEADER
                self._status2 = ""
            else:
                self.ui.connected = False
                self._status  = "WiFi OK - Pi 5 API down"
                self._status_color = C_WARN
                self._status2 = "Search & logging unavailable"
                self._status2_color = C_DIM
        except Exception:
            self.ui.connected = False
            self._status  = "WiFi OK - Pi 5 unreachable"
            self._status_color = C_WARN
            self._status2 = "Is picobird-pro service running?"
            self._status2_color = C_DIM

    def _load_recent(self):
        """Fetch the 4 most recently logged birds."""
        try:
            data = get(self.ui.api_host, self.ui.api_port,
                       "/api/observations/?limit=4&offset=0", timeout=4)
            self._recent = [o.get("common_name", "?") for o in as_list(data)]
        except Exception:
            self._recent = []

    # ── Drawing ───────────────────────────────────────────────────────────────

    def draw(self):
        if not self._dirty:
            now = time.ticks_ms()
            if time.ticks_diff(now, self._last_ping) > 30_000:
                self._last_ping = now
                old_status = self._status
                old_recent = list(self._recent)
                self._refresh()
                if self._status != old_status or self._recent != old_recent:
                    self._dirty = True
            return

        d = self.ui.display
        d.fill(*C_BG)

        # ── Header ───────────────────────────────────────────────────────────
        d.text("picoBird Pro", 10, 6, fg=C_HEADER)

        # Connection status (one or two lines)
        d.text(self._status, 10, 18, fg=self._status_color)
        if self._status2:
            d.text(self._status2[:52], 10, 28, fg=self._status2_color)

        d.fill_rect(0, 40, 320, 1, 40, 100, 60)

        # ── Menu ─────────────────────────────────────────────────────────────
        for i, item in enumerate(MENU_ITEMS):
            y = START_Y + i * ROW_H
            if i == self._sel:
                d.fill_rect(0, y - 2, 320, ROW_H, *C_SEL_BG)
                d.text("> " + item, 10, y, fg=C_SEL_FG)
            else:
                d.text("  " + item, 10, y, fg=C_FG)

        # ── Recently logged ───────────────────────────────────────────────────
        if self._recent:
            d.fill_rect(0, RECENT_Y - 4, 320, 1, 40, 80, 60)
            d.text("Recently logged:", 10, RECENT_Y, fg=C_DIM)
            for i, name in enumerate(self._recent[:RECENT_MAX]):
                d.text(name[:44], 14, RECENT_Y + 10 + i * 10, fg=C_RECENT)
        elif "connected" in self._status:
            d.fill_rect(0, RECENT_Y - 4, 320, 1, 40, 80, 60)
            d.text("No sightings logged yet", 10, RECENT_Y, fg=C_DIM)

        # ── Footer ───────────────────────────────────────────────────────────
        d.text("Joy/arrows=nav  Enter=open", 10, 308, fg=C_DIM)

        self._dirty = False
        self._last_ping = time.ticks_ms()

    # ── Input ─────────────────────────────────────────────────────────────────

    def on_key(self, state, key):
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
        from app.screens.sound import SoundScreen

        if self._sel == 0:
            self.ui.stack.push(TodayScreen(self.ui))
        elif self._sel == 1:
            self.ui.stack.push(SearchScreen(self.ui))
        elif self._sel == 2:
            self.ui.stack.push(LifeListScreen(self.ui))
        elif self._sel == 3:
            self.ui.stack.push(SoundScreen(self.ui))
        else:
            self._status2 = MENU_ITEMS[self._sel] + ": coming soon"
            self._status2_color = C_WARN
            self._dirty = True
