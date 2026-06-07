"""
Settings screen — connection, server stats, sound/mic, and about.
"""
from app.screen import Screen
from lib.keyboard import PRESSED, HOLD, KEY_UP, KEY_DOWN, KEY_ENTER, KEY_ESC
from app.http import get, post

from app import theme as T

C_BG     = T.C_BG
C_FG     = T.C_FG
C_HEADER = T.C_HEADER
C_DIM    = T.C_DIM
C_SEL_BG = T.C_SEL_BG
C_SEL_FG = T.C_SEL_FG
C_OK     = T.C_OK
C_WARN   = T.C_WARN
C_ERR    = T.C_ERR
C_LABEL  = T.C_LABEL

MENU = ["Connection", "Server Stats", "Sound / Mic", "About"]

VERSION = "1.1.0"


class SettingsScreen(Screen):
    def __init__(self, ui):
        super().__init__(ui)
        self._sel    = 0
        self._dirty  = True
        self._stage  = "menu"   # menu | connection | stats | sound | about
        self._info   = None     # cached data for the active detail view
        self._msg    = ""
        self._msg_color = C_DIM

    def on_enter(self):
        self._stage = "menu"
        self._dirty = True

    # ── Drawing ───────────────────────────────────────────────────────────────
    def draw(self):
        if not self._dirty:
            return
        d = self.ui.display
        d.fill(*C_BG)
        d.text("Settings", 10, 8, fg=C_HEADER)
        d.fill_rect(0, 22, 320, 1, 40, 100, 60)

        if self._stage == "menu":
            for i, item in enumerate(MENU):
                y = 40 + i * 22
                if i == self._sel:
                    d.fill_rect(0, y - 2, 320, 20, *C_SEL_BG)
                    d.text("> " + item, 10, y, fg=C_SEL_FG)
                else:
                    d.text("  " + item, 10, y, fg=C_FG)
            d.text("Up/Dn=nav  Enter=open  Esc=back", 4, 306, fg=C_DIM)
        elif self._stage == "connection":
            self._draw_connection(d)
        elif self._stage == "stats":
            self._draw_stats(d)
        elif self._stage == "sound":
            self._draw_sound(d)
        elif self._stage == "about":
            self._draw_about(d)

        self._dirty = False

    def _kv(self, d, label, value, y):
        d.text(label, 10, y, fg=C_LABEL)
        d.text(str(value)[:30], 120, y, fg=C_FG)

    def _draw_connection(self, d):
        d.text("Connection", 10, 30, fg=C_OK)
        wifi = "yes" if self.ui.wifi_connected() else "no"
        self._kv(d, "WiFi assoc:", wifi, 52)
        self._kv(d, "Server:", "up" if self.ui.connected else "down", 68)
        self._kv(d, "API host:", self.ui.api_host, 84)
        self._kv(d, "API port:", self.ui.api_port, 100)
        self._kv(d, "AP SSID:", self.ui.ap_ssid or "?", 116)
        if self._msg:
            d.text(self._msg[:50], 10, 150, fg=self._msg_color)
        d.text("Enter=reconnect  Esc=back", 4, 306, fg=C_DIM)

    def _draw_stats(self, d):
        d.text("Server Stats", 10, 30, fg=C_OK)
        s = self._info
        if not s:
            d.text("No data (server unreachable)", 10, 56, fg=C_WARN)
        else:
            self._kv(d, "Species DB:", s.get("species_count", "?"), 52)
            self._kv(d, "Life list:", s.get("lifers", "?"), 68)
            self._kv(d, "Total obs:", s.get("total_obs", "?"), 84)
            self._kv(d, "Obs today:", s.get("obs_today", "?"), 100)
            self._kv(d, "CPU:", s.get("cpu", "?"), 116)
            self._kv(d, "Memory:", s.get("mem", "?"), 132)
            self._kv(d, "Uptime:", s.get("uptime", "?"), 148)
            self._kv(d, "AP clients:", s.get("ap_clients", "?"), 164)
            self._kv(d, "Disk free:", "{} GB".format(s.get("disk_free_gb", "?")), 180)
            self._kv(d, "BirdNET:", "ok" if s.get("birdnet_ok") else "missing", 196)
        d.text("Enter=refresh  Esc=back", 4, 306, fg=C_DIM)

    def _draw_sound(self, d):
        d.text("Sound / Mic", 10, 30, fg=C_OK)
        s = self._info or {}
        dev = s.get("device")
        self._kv(d, "USB mic:", dev if dev else "none", 56)
        self._kv(d, "Passive:", s.get("status", "?"), 72)
        dets = s.get("detections") or []
        self._kv(d, "Detections:", len(dets), 88)
        if self._msg:
            d.text(self._msg[:50], 10, 120, fg=self._msg_color)
        d.text("Enter=toggle passive  Esc=back", 4, 306, fg=C_DIM)

    def _draw_about(self, d):
        d.text("About", 10, 30, fg=C_OK)
        self._kv(d, "picoBird Pro", "", 56)
        self._kv(d, "Version:", VERSION, 72)
        self._kv(d, "AP SSID:", self.ui.ap_ssid or "?", 88)
        self._kv(d, "API:", "{}:{}".format(self.ui.api_host, self.ui.api_port), 104)
        d.text("Esc=back", 4, 306, fg=C_DIM)

    # ── Input ─────────────────────────────────────────────────────────────────
    def on_key(self, state, key):
        if state not in (PRESSED, HOLD):
            return

        if self._stage == "menu":
            if key == KEY_ESC and state == PRESSED:
                self.ui.stack.pop()
            elif key == KEY_UP:
                self._sel = (self._sel - 1) % len(MENU)
                self._dirty = True
            elif key == KEY_DOWN:
                self._sel = (self._sel + 1) % len(MENU)
                self._dirty = True
            elif key == KEY_ENTER and state == PRESSED:
                self._open(self._sel)
            return

        # detail stages
        if key == KEY_ESC and state == PRESSED:
            self._stage = "menu"
            self._msg = ""
            self._dirty = True
        elif key == KEY_ENTER and state == PRESSED:
            self._detail_action()

    def _open(self, idx):
        self._msg = ""
        if idx == 0:
            self._stage = "connection"
        elif idx == 1:
            self._stage = "stats"
            self._load_stats()
        elif idx == 2:
            self._stage = "sound"
            self._load_sound()
        elif idx == 3:
            self._stage = "about"
        self._dirty = True

    def _detail_action(self):
        if self._stage == "connection":
            ok = self.ui.ping_server()
            self._msg = "Reconnected" if ok else "Still unreachable"
            self._msg_color = C_OK if ok else C_ERR
        elif self._stage == "stats":
            self._load_stats()
        elif self._stage == "sound":
            self._toggle_passive()
        self._dirty = True

    # ── Data ──────────────────────────────────────────────────────────────────
    def _load_stats(self):
        try:
            self._info = get(self.ui.api_host, self.ui.api_port, "/api/vitals/", timeout=5)
        except Exception:
            self._info = None

    def _load_sound(self):
        try:
            self._info = get(self.ui.api_host, self.ui.api_port,
                             "/api/sound/detections", timeout=5)
        except Exception:
            self._info = None

    def _toggle_passive(self):
        cur = (self._info or {}).get("status", "")
        action = "stop" if cur == "running" else "start"
        try:
            post(self.ui.api_host, self.ui.api_port, "/api/sound/listen",
                 {"action": action}, timeout=5)
            self._msg = "Passive " + ("stopped" if action == "stop" else "started")
            self._msg_color = C_OK
        except Exception:
            self._msg = "Could not toggle"
            self._msg_color = C_ERR
        self._load_sound()
