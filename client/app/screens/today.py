"""
My Sightings screen — your logged observations, most recent first.
Select an entry and press Enter to view the species detail.
"""
from app.screens._list import ScrollableListScreen
from app.http import get, as_list


class TodayScreen(ScrollableListScreen):
    TITLE      = "My Sightings"
    FOOTER     = "Up/Dn=scroll  Enter=detail  Esc=back"
    SELECTABLE = True

    def load(self):
        if not self.ui.connected:
            self._items = []
            self._data = []
            self._error = ""
            self._empty_msg = "No WiFi - cannot load observations"
            return
        try:
            data = get(self.ui.api_host, self.ui.api_port,
                       "/api/observations/?limit=100&offset=0", timeout=8)
            rows = as_list(data)
            if rows:
                self._data = rows
                self._items = [
                    o.get("common_name", "?") + "  " + str(o.get("observed_at", ""))[:10]
                    for o in rows
                ]
                self._error = ""
                self._empty_msg = ""
            elif data is not None:
                self._items = []
                self._data = []
                self._error = ""
                self._empty_msg = "No sightings logged yet.\nSearch a species and press L to log!"
            else:
                self._items = []
                self._data = []
                self._error = "Pi 5 unreachable"
                self._empty_msg = "Is picobird-pro service running?"
        except Exception:
            self._items = []
            self._data = []
            self._error = "Pi 5 unreachable"
            self._empty_msg = "Is picobird-pro service running?"

    def on_select(self, index):
        from app.screens.species_detail import SpeciesDetailScreen
        self.ui.stack.push(SpeciesDetailScreen(self.ui, self._data[index]))
