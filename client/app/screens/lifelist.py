"""
Life List screen — unique species the user has ever logged.
Header shows the running species total. Offline-aware messaging.
"""
from app.screens._list import ScrollableListScreen
from app.http import get, as_list


class LifeListScreen(ScrollableListScreen):
    TITLE      = "Life List"
    FOOTER     = "Up/Dn=scroll  Esc=back"
    SELECTABLE = False

    def load(self):
        if not self.ui.connected:
            self._items = []
            self._data = []
            self._error = ""
            self._empty_msg = "No WiFi - life list unavailable"
            return
        try:
            data = get(self.ui.api_host, self.ui.api_port, "/api/lifelist/", timeout=6)
            rows = as_list(data)
            if rows:
                self._data = rows
                self._items = [e.get("common_name", e.get("comName", "?")) for e in rows]
                self._error = ""
                self._empty_msg = ""
            elif data is not None:
                self._items = []
                self._data = []
                self._error = ""
                self._empty_msg = "Life list is empty.\nLog your first bird via Search!"
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
