"""Life list browser screen."""

from app.screen import WHITE, BLACK, ACCENT, GRAY, GREEN
from lib.keyboard import KEY_UP, KEY_DOWN, KEY_ENTER, KEY_ESC


class LifeListScreen:
    def __init__(self, ui):
        self.ui      = ui
        self.screen  = ui.screen
        self.page    = 0
        self.rows    = []
        self.total   = 0
        self.sel     = 0

    def on_enter(self):
        self._load()
        self.draw()

    def on_exit(self):
        pass

    def _load(self):
        try:
            data     = self.ui.http.get_json(f"/api/lifelist/?page={self.page}")
            self.rows  = data.get("results", [])
            self.total = data.get("total", 0)
        except Exception:
            self.rows = []

    def draw(self):
        s = self.screen
        s.fill(BLACK)
        s.header(f"Life List ({self.total})")

        item_h = 18
        for i, row in enumerate(self.rows[:10]):
            y   = 14 + i * item_h
            fg  = BLACK if i == self.sel else WHITE
            bg  = ACCENT if i == self.sel else BLACK
            name = row.get("common_name", row.get("species_code", ""))[:30]
            s.fill_rect(2, y, s.width - 4, item_h - 1, bg)
            s.text(name, 4, y + 4, fg, bg)

        pages = (self.total + 49) // 50
        s.status_bar(f"p{self.page+1}/{max(1,pages)}  ESC=back")

    def handle_key(self, key: int, mod: int):
        if key == KEY_UP:
            if self.sel > 0:
                self.sel -= 1
            elif self.page > 0:
                self.page -= 1
                self.sel   = 0
                self._load()
            self.draw()
        elif key == KEY_DOWN:
            if self.sel < len(self.rows) - 1:
                self.sel += 1
            elif (self.page + 1) * 50 < self.total:
                self.page += 1
                self.sel   = 0
                self._load()
            self.draw()
        elif key == KEY_ENTER and self.rows:
            from app.screens.species_detail import SpeciesDetailScreen
            self.ui.push(SpeciesDetailScreen(self.ui, self.rows[self.sel]["species_code"]))
        elif key == KEY_ESC:
            self.ui.pop()
