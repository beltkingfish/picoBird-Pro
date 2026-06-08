"""
Log Sighting screen.
Confirms species, lets user enter a count and optional note, then POSTs
to /api/observations/.
"""
import time
from app.screen import Screen
from lib.keyboard import PRESSED, KEY_ESC, KEY_ENTER, KEY_UP, KEY_DOWN, KEY_BACKSPACE
from app.http import post

from app import theme as T

C_BG     = T.C_BG
C_FG     = T.C_FG
C_HEADER = T.C_HEADER
C_DIM    = T.C_DIM
C_SEL    = T.C_SEL
C_SEL_BG = T.C_SEL_BG
C_CURSOR = T.C_CURSOR
C_OK     = T.C_OK
C_ERR    = T.C_ERR

FIELD_COUNT  = 0
FIELD_NOTES  = 1
FIELD_LOG    = 2
FIELD_CANCEL = 3


class LogSightingScreen(Screen):
    def __init__(self, ui, species_code, common_name):
        super().__init__(ui)
        self._code   = species_code
        self._name   = common_name
        self._count  = "1"
        self._notes  = ""
        self._field      = FIELD_COUNT
        self._last_field = FIELD_COUNT
        self._dirty      = True
        self._needs_full = True
        self._msg        = ""
        self._msg_color  = C_DIM
        self._done       = False
        self._close_at   = None   # ticks_ms deadline to auto-close after success

    def on_enter(self):
        self._dirty      = True
        self._needs_full = True

    # Y positions for each field row (used by partial repaint).
    _FIELD_Y = {FIELD_COUNT: 42, FIELD_NOTES: 58, FIELD_LOG: 82, FIELD_CANCEL: 106}

    def _draw_field_row(self, field):
        d = self.ui.display
        if field == FIELD_COUNT:
            y = 42
            d.fill_rect(0, y - 1, 320, 14, *C_BG)
            d.text("Count:", 4, y, fg=C_DIM)
            fg = C_CURSOR if self._field == FIELD_COUNT else C_FG
            d.text(self._count + ("_" if self._field == FIELD_COUNT else ""), 50, y, fg=fg)
        elif field == FIELD_NOTES:
            y = 58
            d.fill_rect(0, y - 1, 320, 14, *C_BG)
            d.text("Notes:", 4, y, fg=C_DIM)
            fg = C_CURSOR if self._field == FIELD_NOTES else C_FG
            shown = self._notes[-30:] if len(self._notes) > 30 else self._notes
            d.text(shown + ("_" if self._field == FIELD_NOTES else ""), 50, y, fg=fg)
        elif field in (FIELD_LOG, FIELD_CANCEL):
            labels = {FIELD_LOG: "Log It", FIELD_CANCEL: "Cancel"}
            base_y = {FIELD_LOG: 82, FIELD_CANCEL: 106}
            for f, label in labels.items():
                y = base_y[f]
                if self._field == f:
                    d.fill_rect(0, y - 2, 320, 20, *C_SEL_BG)
                    d.text("> " + label, 10, y, fg=C_SEL)
                else:
                    d.fill_rect(0, y - 2, 320, 20, *C_BG)
                    d.text("  " + label, 10, y, fg=C_FG)

    def draw(self):
        # Non-blocking auto-close after a successful log (no sleep in handlers).
        if self._close_at is not None and time.ticks_diff(time.ticks_ms(), self._close_at) >= 0:
            self._close_at = None
            self.ui.stack.pop()   # back to species detail
            self.ui.stack.pop()   # back to search
            return
        if not self._dirty:
            return

        if not self._needs_full:
            # Only focus moved between fields — repaint old and new field rows.
            self._draw_field_row(self._last_field)
            self._draw_field_row(self._field)
            self._last_field = self._field
            self._dirty = False
            return

        d = self.ui.display
        d.fill(*C_BG)

        d.text("Log Sighting", 4, 6, fg=C_HEADER)
        d.text(self._name[:44], 4, 20, fg=C_FG)
        d.fill_rect(0, 32, 320, 1, 40, 100, 60)

        # Count field
        y = 42
        d.text("Count:", 4, y, fg=C_DIM)
        count_fg = C_CURSOR if self._field == FIELD_COUNT else C_FG
        d.text(self._count + ("_" if self._field == FIELD_COUNT else ""), 50, y, fg=count_fg)

        # Notes field
        y = 58
        d.text("Notes:", 4, y, fg=C_DIM)
        notes_fg = C_CURSOR if self._field == FIELD_NOTES else C_FG
        display_notes = self._notes[-30:] if len(self._notes) > 30 else self._notes
        d.text(display_notes + ("_" if self._field == FIELD_NOTES else ""), 50, y, fg=notes_fg)

        d.fill_rect(0, 74, 320, 1, 40, 60, 40)

        # Buttons
        y = 82
        for i, (label, field) in enumerate([("Log It", FIELD_LOG), ("Cancel", FIELD_CANCEL)]):
            by = y + i * 24
            if self._field == field:
                d.fill_rect(0, by - 2, 320, 20, *C_SEL_BG)
                d.text("> " + label, 10, by, fg=C_SEL)
            else:
                d.text("  " + label, 10, by, fg=C_FG)

        if self._msg:
            d.text(self._msg[:50], 4, 140, fg=self._msg_color)

        d.text("Up/Dn=field  Enter=next  Esc=back", 4, 306, fg=C_DIM)
        self._last_field = self._field
        self._needs_full = False
        self._dirty      = False

    def on_key(self, state, key):
        if state != PRESSED or self._done:
            return

        if key == KEY_ESC:
            self.ui.stack.pop()
            return

        if key == KEY_UP:
            self._last_field = self._field
            self._field = (self._field - 1) % 4
            self._needs_full = False
            self._dirty = True
            return

        if key == KEY_DOWN:
            self._last_field = self._field
            self._field = (self._field + 1) % 4
            self._needs_full = False
            self._dirty = True
            return

        if key == KEY_ENTER:
            if self._field == FIELD_LOG:
                self._submit()
            elif self._field == FIELD_CANCEL:
                self.ui.stack.pop()
            else:
                self._last_field = self._field
                self._field = (self._field + 1) % 4
                self._needs_full = False
                self._dirty = True
            return

        if key == KEY_BACKSPACE:
            if self._field == FIELD_COUNT and self._count:
                self._count = self._count[:-1]
                self._needs_full = True
                self._dirty = True
            elif self._field == FIELD_NOTES and self._notes:
                self._notes = self._notes[:-1]
                self._needs_full = True
                self._dirty = True
            return

        if 0x20 <= key <= 0x7E:
            ch = chr(key)
            if self._field == FIELD_COUNT and ch.isdigit() and len(self._count) < 4:
                self._count += ch
                self._needs_full = True
                self._dirty = True
            elif self._field == FIELD_NOTES and len(self._notes) < 60:
                self._notes += ch
                self._needs_full = True
                self._dirty = True

    def _submit(self):
        try:
            count = int(self._count) if self._count else 1
        except ValueError:
            count = 1

        payload = {
            "species_code": self._code,
            "count": count,
            "notes": self._notes,
        }
        if self.ui.active_session:
            payload["session_id"] = self.ui.active_session.get("id")
        try:
            result = post(self.ui.api_host, self.ui.api_port, "/api/observations/", payload)
            if result:
                self._msg = "Logged! Count: {}".format(count)
                self._msg_color = C_OK
                self._done = True
                self._dirty = True
                # Schedule a non-blocking close ~1.2s out; draw() handles it.
                self._close_at = time.ticks_add(time.ticks_ms(), 1200)
            else:
                self._msg = "Server error - try again"
                self._msg_color = C_ERR
                self._dirty = True
        except Exception as e:
            self._msg = str(e)[:48]
            self._msg_color = C_ERR
            self._dirty = True
