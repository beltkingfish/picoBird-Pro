"""Species detail screen — shows info + lifer status + quick-log button."""

from app.screen import WHITE, BLACK, ACCENT, GRAY, GREEN, RED, YELLOW
from lib.keyboard import KEY_ENTER, KEY_ESC, KEY_UP, KEY_DOWN


class SpeciesDetailScreen:
    def __init__(self, ui, species_code: str):
        self.ui           = ui
        self.screen       = ui.screen
        self.code         = species_code
        self.info: dict   = {}
        self.is_lifer     = False
        self.sel          = 0  # 0=Log it, 1=Back

    def on_enter(self):
        try:
            self.info = self.ui.http.get_json(f"/api/species/{self.code}")
            lifer_data = self.ui.http.get_json(f"/api/lifelist/check/{self.code}")
            self.is_lifer = lifer_data.get("lifer", True)
        except Exception:
            pass
        self.draw()

    def on_exit(self):
        pass

    def draw(self):
        s = self.screen
        s.fill(BLACK)
        s.header("Species")

        common = self.info.get("common_name", self.code)
        sci    = self.info.get("sci_name", "")
        family = self.info.get("family_name", "")

        # Common name (large)
        s.text(common[:30], 4, 18, WHITE, BLACK, 1)
        s.text(sci[:30],    4, 30, GRAY,  BLACK, 1)
        s.text(family[:28], 4, 42, GRAY,  BLACK, 1)

        lifer_label = "NEW LIFER!" if self.is_lifer else "In life list"
        lifer_color = GREEN if self.is_lifer else ACCENT
        s.text(lifer_label, 4, 58, lifer_color)

        # Buttons
        buttons = ["Log Observation", "Back"]
        for i, label in enumerate(buttons):
            y  = 90 + i * 24
            bg = ACCENT if i == self.sel else BLACK
            fg = BLACK  if i == self.sel else WHITE
            s.fill_rect(4, y, s.width - 8, 20, bg)
            s.text(label, 8, y + 6, fg, bg)

        s.status_bar("ENTER=select  ESC=back")

    def handle_key(self, key: int, mod: int):
        if key == KEY_UP:
            self.sel = (self.sel - 1) % 2
            self.draw()
        elif key == KEY_DOWN:
            self.sel = (self.sel + 1) % 2
            self.draw()
        elif key == KEY_ENTER:
            if self.sel == 0:
                self._log_observation()
            else:
                self.ui.pop()
        elif key == KEY_ESC:
            self.ui.pop()

    def _log_observation(self):
        try:
            self.ui.http.post_json("/api/observations/", {"species_code": self.code})
            self.screen.status_bar("Logged!")
            self.screen.show()
        except Exception as e:
            self.screen.status_bar(f"Error: {e}")
            self.screen.show()
