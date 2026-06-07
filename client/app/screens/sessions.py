"""
Sessions screen — start/end a birding session and review past ones.
While a session is active, logged sightings auto-attach to it.
"""
from app.screen import Screen
from app.screens._list import ScrollableListScreen
from lib.keyboard import (PRESSED, HOLD, KEY_UP, KEY_DOWN, KEY_ENTER, KEY_ESC,
                          KEY_BACKSPACE)
from app.http import get, post, patch, as_list

from app import theme as T

C_BG     = T.C_BG
C_FG     = T.C_FG
C_HEADER = T.C_HEADER
C_DIM    = T.C_DIM
C_SEL    = T.C_SEL
C_SEL_BG = T.C_SEL_BG
C_SEL_FG = T.C_SEL_FG
C_OK     = T.C_OK
C_ERR    = T.C_ERR
C_CURSOR = T.C_CURSOR

MAX_NAME = 40


class SessionsScreen(Screen):
    def __init__(self, ui):
        super().__init__(ui)
        self._sel    = 0
        self._dirty  = True
        self._stage  = "menu"   # menu | naming | summary
        self._name   = ""
        self._msg    = ""
        self._msg_color = C_DIM
        self._summary = None

    def on_enter(self):
        self._stage = "menu"
        self._dirty = True

    # ── Menu options depend on whether a session is active ────────────────────
    def _menu(self):
        if self.ui.active_session:
            return ["End Active Session", "Past Sessions"]
        return ["Start New Session", "Past Sessions"]

    # ── Drawing ───────────────────────────────────────────────────────────────
    def draw(self):
        if not self._dirty:
            return
        d = self.ui.display
        d.fill(*C_BG)
        d.text("Sessions", 10, 8, fg=C_HEADER)

        if self.ui.active_session:
            name = self.ui.active_session.get("name") or "Session"
            d.text("Active: " + name[:34], 10, 24, fg=C_OK)
        else:
            d.text("No active session", 10, 24, fg=C_DIM)
        d.fill_rect(0, 38, 320, 1, 40, 100, 60)

        if self._stage == "menu":
            menu = self._menu()
            for i, item in enumerate(menu):
                y = 56 + i * 22
                if i == self._sel:
                    d.fill_rect(0, y - 2, 320, 20, *C_SEL_BG)
                    d.text("> " + item, 10, y, fg=C_SEL_FG)
                else:
                    d.text("  " + item, 10, y, fg=C_FG)
            if self._msg:
                d.text(self._msg[:50], 10, 150, fg=self._msg_color)
            d.text("Up/Dn=nav  Enter=select  Esc=back", 4, 306, fg=C_DIM)

        elif self._stage == "naming":
            d.text("New session name:", 10, 56, fg=C_FG)
            shown = self._name[-36:] if len(self._name) > 36 else self._name
            d.text(">" + shown + "_", 10, 74, fg=C_CURSOR)
            d.text("Type a name, Enter=start, Esc=cancel", 4, 306, fg=C_DIM)

        elif self._stage == "summary" and self._summary:
            s = self._summary
            d.text("Session ended", 10, 56, fg=C_OK)
            d.text("Species: {}".format(s.get("species_count", 0)), 10, 78, fg=C_FG)
            d.text("Sightings: {}".format(s.get("obs_count", 0)), 10, 94, fg=C_FG)
            top = s.get("top_species") or []
            y = 116
            d.text("Top species:", 10, y, fg=C_DIM)
            y += 14
            for row in top[:8]:
                nm = (row.get("common_name") or row.get("species_code") or "?")[:28]
                d.text("{}  x{}".format(nm, row.get("total", 0)), 14, y, fg=C_FG)
                y += 12
            d.text("Press any key to continue", 4, 306, fg=C_DIM)

        self._dirty = False

    # ── Input ─────────────────────────────────────────────────────────────────
    def on_key(self, state, key):
        if state not in (PRESSED, HOLD):
            return

        if self._stage == "summary":
            if state == PRESSED:
                self._stage = "menu"
                self._sel = 0
                self._dirty = True
            return

        if self._stage == "naming":
            self._naming_key(state, key)
            return

        # menu stage
        menu = self._menu()
        if key == KEY_ESC and state == PRESSED:
            self.ui.stack.pop()
        elif key == KEY_UP:
            self._sel = (self._sel - 1) % len(menu)
            self._dirty = True
        elif key == KEY_DOWN:
            self._sel = (self._sel + 1) % len(menu)
            self._dirty = True
        elif key == KEY_ENTER and state == PRESSED:
            self._activate(menu[self._sel])

    def _naming_key(self, state, key):
        if key == KEY_ESC and state == PRESSED:
            self._stage = "menu"
            self._dirty = True
        elif key == KEY_ENTER and state == PRESSED:
            self._start_session()
        elif key == KEY_BACKSPACE:
            self._name = self._name[:-1]
            self._dirty = True
        elif 0x20 <= key <= 0x7E and state == PRESSED and len(self._name) < MAX_NAME:
            self._name += chr(key)
            self._dirty = True

    # ── Actions ─────────────────────────────────────────────────────────────
    def _activate(self, item):
        if item == "Start New Session":
            self._name = ""
            self._stage = "naming"
            self._dirty = True
        elif item == "End Active Session":
            self._end_session()
        elif item == "Past Sessions":
            self.ui.stack.push(PastSessionsScreen(self.ui))
            self._dirty = True

    def _start_session(self):
        name = self._name.strip() or "Session"
        try:
            row = post(self.ui.api_host, self.ui.api_port, "/api/sessions/",
                       {"name": name})
            if row and row.get("id"):
                self.ui.active_session = row
                self._msg = "Started: " + name
                self._msg_color = C_OK
            else:
                self._msg = "Could not start session"
                self._msg_color = C_ERR
        except Exception:
            self._msg = "Connection error"
            self._msg_color = C_ERR
        self._stage = "menu"
        self._sel = 0
        self._dirty = True

    def _end_session(self):
        sess = self.ui.active_session
        if not sess:
            return
        sid = sess.get("id")
        try:
            patch(self.ui.api_host, self.ui.api_port,
                  "/api/sessions/{}/end".format(sid), {})
            self._summary = get(self.ui.api_host, self.ui.api_port,
                                "/api/sessions/{}/summary".format(sid), timeout=6)
        except Exception:
            self._summary = None
        self.ui.active_session = None
        if self._summary:
            self._stage = "summary"
        else:
            self._msg = "Session ended"
            self._msg_color = C_OK
            self._stage = "menu"
            self._sel = 0
        self._dirty = True


class PastSessionsScreen(ScrollableListScreen):
    TITLE      = "Past Sessions"
    FOOTER     = "Up/Dn=scroll  Esc=back"
    SELECTABLE = False

    def load(self):
        if not self.ui.connected:
            self._items = []
            self._empty_msg = "No WiFi - sessions unavailable"
            return
        try:
            data = get(self.ui.api_host, self.ui.api_port, "/api/sessions/", timeout=6)
            rows = as_list(data) if isinstance(data, dict) else (data or [])
            if rows:
                self._data = rows
                self._items = []
                for r in rows:
                    nm = r.get("name") or r.get("location") or "Session {}".format(r.get("id"))
                    state = "active" if not r.get("ended_at") else "done"
                    self._items.append("{}  [{}]".format(nm[:36], state))
                self._empty_msg = ""
            else:
                self._empty_msg = "No sessions yet"
        except Exception:
            self._error = "Pi 5 unreachable"
            self._empty_msg = "Is picobird-pro running?"
