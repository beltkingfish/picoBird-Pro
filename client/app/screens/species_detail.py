"""
Species detail screen.
Shows name, family, sci name.
Quick-log: press L or joystick center to log count=1 instantly.
Full log: navigate to "Log Sighting" for count + notes.
"""
from app.screen import Screen
from lib.keyboard import PRESSED, KEY_ESC, KEY_ENTER, KEY_UP, KEY_DOWN
from app.http import post

from app import theme as T

C_BG      = T.C_BG
C_FG      = T.C_FG
C_HEADER  = T.C_HEADER
C_DIM     = T.C_DIM
C_SEL     = T.C_SEL
C_SEL_BG  = T.C_SEL_BG
C_LABEL   = T.C_LABEL
C_OK      = T.C_OK
C_ERR     = T.C_ERR
C_QUICKLOG = T.C_QUICKLOG   # gold highlight for quick-log hint

ACTIONS = ["Log Sighting", "Back"]


class SpeciesDetailScreen(Screen):
    def __init__(self, ui, species):
        super().__init__(ui)
        self._code   = species.get("species_code", species.get("speciesCode", ""))
        self._common = species.get("common_name",  species.get("comName", "Unknown"))
        self._sci    = species.get("sci_name",     species.get("sciName", ""))
        self._family = species.get("family_name",  species.get("familyComName", ""))
        self._sel       = 0
        self._last_sel  = 0
        self._dirty     = True
        self._needs_full = True
        self._msg       = ""
        self._msg_color = C_DIM
        # Precompute action menu Y start (depends on name length and family presence).
        base = 32 if len(self._common) > 44 else 22
        self._action_y = base + 6 + 14 + (14 if self._family else 0) + 16 + 6 + 14 + 8

    def on_enter(self):
        self._dirty      = True
        self._needs_full = True

    def _draw_action_row(self, i):
        d = self.ui.display
        action = ACTIONS[i]
        ay = self._action_y + i * 22
        if i == self._sel:
            d.fill_rect(0, ay - 2, 320, 20, *C_SEL_BG)
            d.text("> " + action, 10, ay, fg=C_SEL)
        else:
            d.fill_rect(0, ay - 2, 320, 20, *C_BG)
            d.text("  " + action, 10, ay, fg=C_FG)

    def draw(self):
        if not self._dirty:
            return

        if not self._needs_full:
            self._draw_action_row(self._last_sel)
            self._draw_action_row(self._sel)
            self._last_sel = self._sel
            self._dirty = False
            return

        d = self.ui.display
        d.fill(*C_BG)

        # Species name (wrap if long)
        name = self._common
        if len(name) <= 44:
            d.text(name, 4, 8, fg=C_HEADER)
            y = 22
        else:
            d.text(name[:44], 4, 8, fg=C_HEADER)
            d.text(name[44:88], 4, 18, fg=C_HEADER)
            y = 32

        d.fill_rect(0, y, 320, 1, 40, 100, 60)
        y += 6

        # Scientific name
        d.text("Sci:", 4, y, fg=C_LABEL)
        d.text(self._sci[:42], 30, y, fg=C_DIM)
        y += 14

        # Family
        if self._family:
            d.text("Family:", 4, y, fg=C_LABEL)
            d.text(self._family[:36], 50, y, fg=C_DIM)
            y += 14

        # Species code
        d.text("Code:", 4, y, fg=C_LABEL)
        d.text(self._code, 40, y, fg=C_DIM)
        y += 16

        # Quick-log hint
        d.fill_rect(0, y, 320, 1, 60, 60, 20)
        y += 6
        d.text("Quick-log: press L  (count=1, no notes)", 4, y, fg=C_QUICKLOG)
        y += 14

        d.fill_rect(0, y, 320, 1, 40, 60, 40)
        y += 8

        # Action menu
        for i, action in enumerate(ACTIONS):
            ay = y + i * 22
            if i == self._sel:
                d.fill_rect(0, ay - 2, 320, 20, *C_SEL_BG)
                d.text("> " + action, 10, ay, fg=C_SEL)
            else:
                d.text("  " + action, 10, ay, fg=C_FG)

        if self._msg:
            d.text(self._msg[:50], 4, 288, fg=self._msg_color)

        d.text("L=quick-log  Enter=select  Esc=back", 4, 306, fg=C_DIM)
        self._last_sel   = self._sel
        self._needs_full = False
        self._dirty      = False

    def on_key(self, state, key):
        if state != PRESSED:
            return
        if key == KEY_ESC:
            self.ui.stack.pop()
        elif key == ord('l') or key == ord('L'):
            self._quick_log()
        elif key == KEY_UP:
            self._last_sel = self._sel
            self._sel = (self._sel - 1) % len(ACTIONS)
            self._needs_full = False
            self._dirty = True
        elif key == KEY_DOWN:
            self._last_sel = self._sel
            self._sel = (self._sel + 1) % len(ACTIONS)
            self._needs_full = False
            self._dirty = True
        elif key == KEY_ENTER:
            if self._sel == 0:
                from app.screens.log_sighting import LogSightingScreen
                self.ui.stack.push(LogSightingScreen(self.ui, self._code, self._common))
            else:
                self.ui.stack.pop()

    def _quick_log(self):
        """Log count=1 immediately with no notes — one keypress in the field."""
        payload = {"species_code": self._code, "count": 1}
        if self.ui.active_session:
            payload["session_id"] = self.ui.active_session.get("id")
        try:
            result = post(self.ui.api_host, self.ui.api_port,
                          "/api/observations/", payload)
            if result:
                self._msg = "Logged! (quick)"
                self._msg_color = C_OK
            else:
                self._msg = "Server error"
                self._msg_color = C_ERR
        except Exception as e:
            self._msg = str(e)[:48]
            self._msg_color = C_ERR
        self._dirty      = True
        self._needs_full = True
