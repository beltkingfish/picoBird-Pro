"""
Log Sighting screen.
Confirms species, lets user enter a count and optional note, then POSTs
to /api/observations/.
"""
from app.screen import Screen
from lib.keyboard import PRESSED, KEY_ESC, KEY_ENTER, KEY_UP, KEY_DOWN, KEY_BACKSPACE
from app.http import post

C_BG     = (0, 0, 0)
C_FG     = (255, 255, 255)
C_HEADER = (80, 200, 120)
C_DIM    = (100, 100, 100)
C_SEL    = (120, 255, 160)
C_SEL_BG = (30, 90, 50)
C_CURSOR = (255, 255, 0)
C_OK     = (80, 255, 80)
C_ERR    = (255, 80, 80)

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
        self._field  = FIELD_COUNT
        self._dirty  = True
        self._msg    = ""
        self._msg_color = C_DIM
        self._done   = False

    def on_enter(self):
        self._dirty = True

    def draw(self):
        if not self._dirty:
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
        self._dirty = False

    def on_key(self, state, key):
        if state != PRESSED or self._done:
            return

        if key == KEY_ESC:
            self.ui.stack.pop()
            return

        if key == KEY_UP:
            self._field = (self._field - 1) % 4
            self._dirty = True
            return

        if key == KEY_DOWN:
            self._field = (self._field + 1) % 4
            self._dirty = True
            return

        if key == KEY_ENTER:
            if self._field == FIELD_LOG:
                self._submit()
            elif self._field == FIELD_CANCEL:
                self.ui.stack.pop()
            else:
                self._field = (self._field + 1) % 4
                self._dirty = True
            return

        if key == KEY_BACKSPACE:
            if self._field == FIELD_COUNT and self._count:
                self._count = self._count[:-1]
                self._dirty = True
            elif self._field == FIELD_NOTES and self._notes:
                self._notes = self._notes[:-1]
                self._dirty = True
            return

        if 0x20 <= key <= 0x7E:
            ch = chr(key)
            if self._field == FIELD_COUNT and ch.isdigit() and len(self._count) < 4:
                self._count += ch
                self._dirty = True
            elif self._field == FIELD_NOTES and len(self._notes) < 60:
                self._notes += ch
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
        try:
            result = post(self.ui.api_host, self.ui.api_port, "/api/observations/", payload)
            if result:
                self._msg = "Logged! Count: {}".format(count)
                self._msg_color = C_OK
                self._done = True
                self._dirty = True
                import time
                time.sleep_ms(1200)
                self.ui.stack.pop()  # back to species detail
                self.ui.stack.pop()  # back to search
            else:
                self._msg = "Server error - try again"
                self._msg_color = C_ERR
                self._dirty = True
        except Exception as e:
            self._msg = str(e)[:48]
            self._msg_color = C_ERR
            self._dirty = True
