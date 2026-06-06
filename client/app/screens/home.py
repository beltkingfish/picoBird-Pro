"""Home screen — main menu."""

from app.screen import Screen, WHITE, BLACK, ACCENT, GRAY, GREEN
from lib.keyboard import KEY_UP, KEY_DOWN, KEY_ENTER, KEY_NONE

MENU_ITEMS = [
    ("Search Species",  "search"),
    ("New Observation", "observe"),
    ("Life List",       "lifelist"),
    ("Sessions",        "sessions"),
    ("Sound ID",        "sound"),
]


class HomeScreen:
    def __init__(self, ui):
        self.ui      = ui
        self.screen  = ui.screen
        self.sel     = 0
        self._lifer_count: int | None = None

    def on_enter(self):
        # Fetch life list count for display.
        try:
            data = self.ui.http.get_json("/api/lifelist/stats")
            self._lifer_count = data.get("total_species", 0)
        except Exception:
            self._lifer_count = None

    def on_exit(self):
        pass

    def draw(self):
        s = self.screen
        s.fill(BLACK)
        s.header("picoBird Pro")

        if self._lifer_count is not None:
            s.text(f"Lifers: {self._lifer_count}", 4, 16, GRAY)

        item_h = 24
        start_y = 40
        for i, (label, _) in enumerate(MENU_ITEMS):
            y   = start_y + i * item_h
            fg  = BLACK if i == self.sel else WHITE
            bg  = ACCENT if i == self.sel else BLACK
            s.fill_rect(4, y, s.width - 8, item_h - 2, bg)
            s.text(label, 8, y + 8, fg, bg)

        s.status_bar("UP/DOWN  ENTER=select")

    def handle_key(self, key: int, mod: int):
        if key == KEY_UP:
            self.sel = (self.sel - 1) % len(MENU_ITEMS)
            self.draw()
        elif key == KEY_DOWN:
            self.sel = (self.sel + 1) % len(MENU_ITEMS)
            self.draw()
        elif key == KEY_ENTER:
            self._launch(MENU_ITEMS[self.sel][1])

    def _launch(self, target: str):
        if target == "search":
            from app.screens.search import SearchScreen
            self.ui.push(SearchScreen(self.ui))
        elif target == "observe":
            from app.screens.observe import ObserveScreen
            self.ui.push(ObserveScreen(self.ui))
        elif target == "lifelist":
            from app.screens.lifelist import LifeListScreen
            self.ui.push(LifeListScreen(self.ui))
        elif target == "sessions":
            from app.screens.sessions import SessionsScreen
            self.ui.push(SessionsScreen(self.ui))
        elif target == "sound":
            from app.screens.sound import SoundScreen
            self.ui.push(SoundScreen(self.ui))
