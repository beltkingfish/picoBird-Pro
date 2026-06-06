"""Session management screen."""

from app.screen import WHITE, BLACK, ACCENT, GRAY, GREEN
from lib.keyboard import KEY_UP, KEY_DOWN, KEY_ENTER, KEY_ESC
import time


class SessionsScreen:
    def __init__(self, ui):
        self.ui      = ui
        self.screen  = ui.screen
        self.rows    = []
        self.sel     = 0
        self._menu   = ["New Session", "View Sessions"]
        self._stage  = "menu"  # menu | list

    def on_enter(self):
        self._load()
        self.draw()

    def on_exit(self):
        pass

    def _load(self):
        try:
            self.rows = self.ui.http.get_json("/api/sessions/")
        except Exception:
            self.rows = []

    def draw(self):
        s = self.screen
        s.fill(BLACK)
        s.header("Sessions")

        if self._stage == "menu":
            for i, label in enumerate(self._menu):
                y  = 30 + i * 24
                fg = BLACK if i == self.sel else WHITE
                bg = ACCENT if i == self.sel else BLACK
                s.fill_rect(4, y, s.width - 8, 20, bg)
                s.text(label, 8, y + 6, fg, bg)
            s.status_bar("ENTER=select  ESC=back")

        elif self._stage == "list":
            item_h = 18
            for i, row in enumerate(self.rows[:10]):
                y    = 14 + i * item_h
                fg   = BLACK if i == self.sel else WHITE
                bg   = ACCENT if i == self.sel else BLACK
                name = (row.get("name") or row.get("location") or f"Session {row['id']}")[:28]
                s.fill_rect(2, y, s.width - 4, item_h - 1, bg)
                s.text(name, 4, y + 4, fg, bg)
            s.status_bar(f"{len(self.rows)} sessions  ESC=back")

    def handle_key(self, key: int, mod: int):
        if self._stage == "menu":
            if key == KEY_UP:
                self.sel = (self.sel - 1) % len(self._menu)
                self.draw()
            elif key == KEY_DOWN:
                self.sel = (self.sel + 1) % len(self._menu)
                self.draw()
            elif key == KEY_ENTER:
                if self.sel == 0:
                    self._new_session()
                else:
                    self._stage = "list"
                    self.sel    = 0
                    self.draw()
            elif key == KEY_ESC:
                self.ui.pop()

        elif self._stage == "list":
            if key == KEY_UP:
                self.sel = max(0, self.sel - 1)
                self.draw()
            elif key == KEY_DOWN:
                self.sel = min(len(self.rows) - 1, self.sel + 1)
                self.draw()
            elif key == KEY_ESC:
                self._stage = "menu"
                self.sel    = 0
                self.draw()

    def _new_session(self):
        try:
            ts = time.time()
            self.ui.http.post_json("/api/sessions/", {"name": f"Session {ts}"})
            self.screen.status_bar("Session started!")
            self.screen.show()
            import time as t; t.sleep_ms(600)
            self._load()
            self._stage = "list"
            self.draw()
        except Exception as e:
            self.screen.status_bar(f"Error: {e}")
            self.screen.show()
