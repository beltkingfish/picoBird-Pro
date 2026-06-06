"""Quick-log observation screen."""

from app.screen import WHITE, BLACK, ACCENT, GRAY, GREEN
from lib.keyboard import KEY_UP, KEY_DOWN, KEY_ENTER, KEY_ESC, KEY_BKSP


class ObserveScreen:
    def __init__(self, ui):
        self.ui       = ui
        self.screen   = ui.screen
        self.query    = ""
        self.results  = []
        self.sel      = 0
        self.typing   = True
        self.count    = 1
        self.notes    = ""
        self._stage   = "search"  # search -> confirm
        self._chosen: dict | None = None

    def on_enter(self):
        self.draw()

    def on_exit(self):
        pass

    def _search(self):
        if not self.query:
            self.results = []
            return
        try:
            data = self.ui.http.get_json(f"/api/species/search?q={self.query}&page=0")
            self.results = data.get("results", [])[:8]
        except Exception:
            self.results = []

    def draw(self):
        s = self.screen
        s.fill(BLACK)

        if self._stage == "search":
            s.header("Log Observation")
            bar = f"Species: {self.query}{'_' if self.typing else ''}"
            s.fill_rect(0, 12, s.width, 12, 0x001F)
            s.text(bar[:s.cols], 2, 14, WHITE, 0x001F)

            for i, row in enumerate(self.results):
                y  = 28 + i * 18
                fg = BLACK if i == self.sel and not self.typing else WHITE
                bg = ACCENT if i == self.sel and not self.typing else BLACK
                s.fill_rect(2, y, s.width - 4, 17, bg)
                s.text(row.get("common_name", "")[:30], 4, y + 4, fg, bg)

            s.status_bar("Type to search  ESC=back")

        elif self._stage == "confirm":
            s.header("Confirm")
            name = self._chosen.get("common_name", "") if self._chosen else ""
            s.text(name[:30], 4, 20, WHITE)
            s.text(f"Count: {self.count}", 4, 38, WHITE)
            s.text("+ / - to adjust", 4, 50, GRAY)
            s.text("ENTER to log  ESC to cancel", 4, 66, GRAY)

    def handle_key(self, key: int, mod: int):
        if self._stage == "search":
            if self.typing:
                if 0x20 <= key <= 0x7E:
                    self.query += chr(key)
                    self._search()
                    self.draw()
                elif key == KEY_BKSP:
                    self.query = self.query[:-1]
                    self._search()
                    self.draw()
                elif key == KEY_DOWN and self.results:
                    self.typing = False
                    self.draw()
                elif key == KEY_ESC:
                    self.ui.pop()
            else:
                if key == KEY_UP:
                    if self.sel > 0:
                        self.sel -= 1
                    else:
                        self.typing = True
                    self.draw()
                elif key == KEY_DOWN:
                    self.sel = min(self.sel + 1, len(self.results) - 1)
                    self.draw()
                elif key == KEY_ENTER and self.results:
                    self._chosen = self.results[self.sel]
                    self._stage  = "confirm"
                    self.draw()
                elif key == KEY_ESC:
                    self.typing = True
                    self.draw()

        elif self._stage == "confirm":
            if key == ord("+"):
                self.count += 1
                self.draw()
            elif key == ord("-") and self.count > 1:
                self.count -= 1
                self.draw()
            elif key == KEY_ENTER:
                self._submit()
            elif key == KEY_ESC:
                self._stage = "search"
                self.draw()

    def _submit(self):
        if not self._chosen:
            return
        try:
            self.ui.http.post_json("/api/observations/", {
                "species_code": self._chosen["species_code"],
                "count":        self.count,
            })
            self.screen.fill(BLACK)
            self.screen.text_center("Logged!", 140, GREEN)
            self.screen.show()
            import time; time.sleep_ms(800)
            self.ui.pop()
        except Exception as e:
            self.screen.status_bar(f"Error: {e}")
            self.screen.show()
