"""Species search screen."""

from app.screen import Screen, WHITE, BLACK, ACCENT, GRAY, GREEN, YELLOW
from lib.keyboard import KEY_UP, KEY_DOWN, KEY_ENTER, KEY_ESC, KEY_BKSP

PAGE_SIZE = 20


class SearchScreen:
    def __init__(self, ui):
        self.ui      = ui
        self.screen  = ui.screen
        self.query   = ""
        self.results = []
        self.sel     = 0
        self.page    = 0
        self.total   = 0
        self._typing = True  # Start in typing mode

    def on_enter(self):
        self.draw()

    def on_exit(self):
        pass

    def _search(self):
        if not self.query:
            self.results = []
            return
        try:
            data = self.ui.http.get_json(
                f"/api/species/search?q={self.query}&page={self.page}"
            )
            self.results = data.get("results", [])
            self.total   = data.get("total", 0)
        except Exception as e:
            self.results = []
            self.screen.status_bar(f"Error: {e}")

    def draw(self):
        s = self.screen
        s.fill(BLACK)
        s.header("Species Search")

        # Search bar
        bar_label = f"Search: {self.query}{'_' if self._typing else ''}"
        s.fill_rect(0, 12, s.width, 12, 0x001F)
        s.text(bar_label[:s.cols], 2, 14, WHITE, 0x001F)

        # Results list
        item_h = 18
        start_y = 26
        for i, row in enumerate(self.results[:10]):
            y  = start_y + i * item_h
            fg = BLACK if i == self.sel else WHITE
            bg = ACCENT if i == self.sel else BLACK
            name = row.get("common_name", "")[:30]
            s.fill_rect(2, y, s.width - 4, item_h - 1, bg)
            s.text(name, 4, y + 4, fg, bg)

        if not self.results and self.query:
            s.text_center("No results", 140, GRAY)

        # Pagination
        pages = (self.total + PAGE_SIZE - 1) // PAGE_SIZE if self.total else 0
        s.status_bar(f"p{self.page+1}/{max(1,pages)}  ESC=back")

    def handle_key(self, key: int, mod: int):
        if self._typing:
            if 0x20 <= key <= 0x7E:
                self.query += chr(key)
                self.page   = 0
                self.sel    = 0
                self._search()
                self.draw()
            elif key == KEY_BKSP:
                self.query  = self.query[:-1]
                self.page   = 0
                self.sel    = 0
                self._search()
                self.draw()
            elif key == KEY_DOWN and self.results:
                self._typing = False
                self.draw()
            elif key == KEY_ESC:
                self.ui.pop()
        else:
            if key == KEY_UP:
                if self.sel > 0:
                    self.sel -= 1
                else:
                    self._typing = True
                self.draw()
            elif key == KEY_DOWN:
                if self.sel < len(self.results) - 1:
                    self.sel += 1
                    self.draw()
            elif key == KEY_ENTER and self.results:
                self._open_species(self.results[self.sel])
            elif key == KEY_ESC:
                self._typing = True
                self.draw()

    def _open_species(self, row: dict):
        from app.screens.species_detail import SpeciesDetailScreen
        self.ui.push(SpeciesDetailScreen(self.ui, row["species_code"]))
