"""Sound ID screen — trigger Pi-side USB mic capture and display BirdNET results."""
import time
from app.screen import Screen
from app import theme as T
from app.http import get, post
from lib.keyboard import PRESSED, HOLD, KEY_UP, KEY_DOWN, KEY_ENTER, KEY_ESC

MENU = ["Listen 10s", "Listen 30s", "Passive On/Off", "View Detections"]

_DURATIONS = {0: 10, 1: 30}   # menu index → seconds for capture items


class SoundScreen(Screen):
    def __init__(self, ui):
        super().__init__(ui)
        self._sel         = 0
        self._last_sel    = 0
        self._dirty       = True
        self._needs_full  = True
        self._device      = None   # None means not checked yet; "" means absent
        self._state       = "menu"   # menu | capturing | results | passive_msg | error
        self._msg         = ""
        self._results     = []       # list of detection dicts
        self._passive_on  = False
        self._scroll_off  = 0

    def on_enter(self):
        self._dirty      = True
        self._needs_full = True
        self._check_device()

    # ── Data ──────────────────────────────────────────────────────────────────

    def _check_device(self):
        if not self.ui.connected:
            self._device = ""
            return
        try:
            data = get(self.ui.api_host, self.ui.api_port, "/api/sound/device", timeout=4)
            self._device = (data or {}).get("device") or ""
        except Exception:
            self._device = ""

    def _capture(self, duration):
        self._state = "capturing"
        self._msg   = "Recording {}s...".format(duration)
        self._dirty = True
        self.draw()
        try:
            path = "/api/sound/capture?duration={}".format(duration)
            data = get(self.ui.api_host, self.ui.api_port, path,
                       timeout=duration + 60)
            if data and "detections" in data:
                self._results = data["detections"]
                self._state   = "results"
                self._scroll_off = 0
            else:
                self._state = "error"
                self._msg   = "Capture failed or no response"
        except Exception:
            self._state = "error"
            self._msg   = "Connection error during capture"
        self._dirty = True

    def _toggle_passive(self):
        action = "stop" if self._passive_on else "start"
        try:
            data = post(self.ui.api_host, self.ui.api_port,
                        "/api/sound/listen", {"action": action}, timeout=5)
            status = (data or {}).get("status", "")
            self._passive_on = (status == "running")
            self._msg  = "Passive: " + ("ON" if self._passive_on else "OFF")
        except Exception:
            self._msg = "Could not toggle passive mode"
        self._state = "passive_msg"
        self._dirty = True

    def _view_detections(self):
        try:
            data = get(self.ui.api_host, self.ui.api_port,
                       "/api/sound/detections", timeout=5)
            if data:
                self._results    = (data.get("detections") or [])
                self._passive_on = data.get("status") == "running"
            else:
                self._results = []
            self._state      = "results"
            self._scroll_off = 0
        except Exception:
            self._state = "error"
            self._msg   = "Could not fetch detections"
        self._dirty = True

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _draw_menu_row(self, i):
        d = self.ui.display
        passive_label = "Passive: " + ("ON" if self._passive_on else "off")
        label = MENU[i] if i != 2 else passive_label
        y = 56 + i * 20
        if i == self._sel:
            d.fill_rect(0, y - 2, T.WIDTH, 18, *T.C_SEL_BG)
            d.text("> " + label, 10, y, fg=T.C_SEL_FG)
        else:
            d.fill_rect(0, y - 2, T.WIDTH, 18, *T.C_BG)
            d.text("  " + label, 10, y, fg=T.C_FG)

    def draw(self):
        if not self._dirty:
            return

        if self._state == "menu" and not self._needs_full and self._device:
            self._draw_menu_row(self._last_sel)
            self._draw_menu_row(self._sel)
            self._last_sel = self._sel
            self._dirty = False
            return

        d = self.ui.display
        d.fill(*T.C_BG)
        d.text("Sound ID", 10, 8, fg=T.C_HEADER)
        d.fill_rect(0, 24, T.WIDTH, 1, 40, 100, 60)

        if not self.ui.connected:
            d.text("Not connected to Pi 5", 10, 50, fg=T.C_ERR)
            d.text("Connect WiFi and try again", 10, 64, fg=T.C_DIM)
        elif self._device == "":
            d.text("No USB mic connected", 10, 50, fg=T.C_WARN)
            d.text("Plug Rode receiver into Pi 5", 10, 64, fg=T.C_DIM)
            d.text("then re-open this screen", 10, 74, fg=T.C_DIM)
        elif self._state == "menu":
            d.text("Mic: " + self._device[:36], 10, 34, fg=T.C_DIM)
            for i in range(len(MENU)):
                self._draw_menu_row(i)
            self._last_sel   = self._sel
            self._needs_full = False
        elif self._state == "capturing":
            d.text(self._msg, 10, 60, fg=T.C_WARN)
            d.text("Please wait...", 10, 76, fg=T.C_DIM)
        elif self._state == "passive_msg":
            d.text(self._msg, 10, 60, fg=T.C_HEADER)
            d.text("Press any key", 10, 76, fg=T.C_DIM)
        elif self._state == "error":
            d.text("Error:", 10, 50, fg=T.C_ERR)
            d.text(self._msg[:44], 10, 64, fg=T.C_DIM)
            d.text("Press any key", 10, 80, fg=T.C_DIM)
        elif self._state == "results":
            self._draw_results(d)
            self._dirty = False
            return

        d.text("Up/Dn=nav  Enter=select  Esc=back", 4, T.FOOTER_Y, fg=T.C_DIM)
        self._dirty = False

    def _draw_results(self, d):
        VISIBLE = 18
        d.text("Detections:", 10, 32, fg=T.C_HEADER)
        if not self._results:
            d.text("No birds detected", 10, 56, fg=T.C_DIM)
        else:
            for i in range(VISIBLE):
                idx = self._scroll_off + i
                if idx >= len(self._results):
                    break
                det  = self._results[idx]
                name = det.get("common_name", "?")[:26]
                conf = int(det.get("confidence", 0) * 100)
                ts   = str(det.get("detected_at", ""))[-8:]   # HH:MM:SS if ISO
                line = "{} {}%".format(name, conf)
                if ts:
                    line = line + "  " + ts
                d.text(line[:44], 10, 48 + i * 14, fg=T.C_FG)
        d.text("Esc=back  Up/Dn=scroll", 4, T.FOOTER_Y, fg=T.C_DIM)
        self._dirty = False

    # ── Input ─────────────────────────────────────────────────────────────────

    def on_key(self, state, key):
        if state not in (PRESSED, HOLD):
            return

        if self._state in ("error", "passive_msg"):
            if state == PRESSED:
                self._state      = "menu"
                self._dirty      = True
                self._needs_full = True
            return

        if self._state == "results":
            if key == KEY_ESC and state == PRESSED:
                self._state      = "menu"
                self._dirty      = True
                self._needs_full = True
            elif key == KEY_UP and self._scroll_off > 0:
                self._scroll_off -= 1
                self._dirty      = True
                self._needs_full = True
            elif key == KEY_DOWN and self._scroll_off < len(self._results) - 1:
                self._scroll_off += 1
                self._dirty      = True
                self._needs_full = True
            return

        if self._state == "menu":
            if key == KEY_ESC and state == PRESSED:
                self.ui.stack.pop()
            elif key == KEY_UP:
                self._last_sel   = self._sel
                self._sel        = (self._sel - 1) % len(MENU)
                self._needs_full = False
                self._dirty      = True
            elif key == KEY_DOWN:
                self._last_sel   = self._sel
                self._sel        = (self._sel + 1) % len(MENU)
                self._needs_full = False
                self._dirty      = True
            elif key == KEY_ENTER and state == PRESSED:
                self._activate()

    def _activate(self):
        if not self._device:
            return
        if self._sel in _DURATIONS:
            self._capture(_DURATIONS[self._sel])
        elif self._sel == 2:
            self._toggle_passive()
        elif self._sel == 3:
            self._view_detections()
