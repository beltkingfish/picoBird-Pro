"""
Settings screen — connection, server stats, sound/mic, and about.
"""
from app.screen import Screen
from lib.keyboard import PRESSED, HOLD, KEY_UP, KEY_DOWN, KEY_ENTER, KEY_ESC, KEY_BACKSPACE
from app.http import get, post, patch

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
C_CURSOR = T.C_CURSOR

MENU = ["Connection", "Server Stats", "Sound / Mic", "Region Filter", "About"]

MAX_REGION = 16   # eBird region codes are short (e.g. US-CO, AU-NSW)

VERSION = "1.1.0"


class SettingsScreen(Screen):
    def __init__(self, ui):
        super().__init__(ui)
        self._sel    = 0
        self._dirty  = True
        self._needs_full = True
        self._last_sel = 0
        self._stage  = "menu"   # menu | connection | stats | sound | region | about
        self._info   = None     # cached data for the active detail view
        self._msg    = ""
        self._msg_color = C_DIM
        self._region_input = ""  # text field for region stage

    def on_enter(self):
        self._stage      = "menu"
        self._dirty      = True
        self._needs_full = True

    # ── Drawing ───────────────────────────────────────────────────────────────
    def _draw_menu_row(self, i):
        d = self.ui.display
        y = 40 + i * 22
        if i == self._sel:
            d.fill_rect(0, y - 2, 320, 20, *C_SEL_BG)
            d.text("> " + MENU[i], 10, y, fg=C_SEL_FG)
        else:
            d.fill_rect(0, y - 2, 320, 20, *C_BG)
            d.text("  " + MENU[i], 10, y, fg=C_FG)

    def draw(self):
        if not self._dirty:
            return
        d = self.ui.display

        if self._stage == "menu" and not self._needs_full:
            self._draw_menu_row(self._last_sel)
            self._draw_menu_row(self._sel)
            self._last_sel = self._sel
            self._dirty = False
            return

        d.fill(*C_BG)
        d.text("Settings", 10, 8, fg=C_HEADER)
        d.fill_rect(0, 22, 320, 1, 40, 100, 60)

        if self._stage == "menu":
            for i in range(len(MENU)):
                self._draw_menu_row(i)
            d.text("Up/Dn=nav  Enter=open  Esc=back", 4, 306, fg=C_DIM)
            self._last_sel   = self._sel
            self._needs_full = False
        elif self._stage == "connection":
            self._draw_connection(d)
        elif self._stage == "stats":
            self._draw_stats(d)
        elif self._stage == "sound":
            self._draw_sound(d)
        elif self._stage == "region":
            self._draw_region(d)
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

    def _draw_region(self, d):
        d.text("Region Filter", 10, 30, fg=C_OK)
        d.text("eBird region code (e.g. US-CO, AU-NSW)", 10, 50, fg=C_DIM)
        d.text("Blank = all ~16k species searchable", 10, 62, fg=C_DIM)
        d.fill_rect(0, 76, 320, 1, 40, 80, 60)
        d.text("Region:", 10, 84, fg=C_LABEL)
        shown = self._region_input[-18:] if len(self._region_input) > 18 else self._region_input
        d.text(shown + "_", 70, 84, fg=C_CURSOR)
        if self._msg:
            d.text(self._msg[:46], 10, 104, fg=self._msg_color)
        d.text("Type code  Enter=save  Esc=back", 4, 306, fg=C_DIM)

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
                self._last_sel = self._sel
                self._sel = (self._sel - 1) % len(MENU)
                self._needs_full = False
                self._dirty = True
            elif key == KEY_DOWN:
                self._last_sel = self._sel
                self._sel = (self._sel + 1) % len(MENU)
                self._needs_full = False
                self._dirty = True
            elif key == KEY_ENTER and state == PRESSED:
                self._open(self._sel)
            return

        if self._stage == "region":
            if key == KEY_ESC and state == PRESSED:
                self._stage = "menu"
                self._msg = ""
                self._dirty = True
                self._needs_full = True
            elif key == KEY_ENTER and state == PRESSED:
                self._save_region()
            elif key == KEY_BACKSPACE:
                self._region_input = self._region_input[:-1]
                self._dirty = True
            elif 0x20 <= key <= 0x7E and state == PRESSED:
                if len(self._region_input) < MAX_REGION:
                    self._region_input += chr(key)
                    self._dirty = True
            return

        # other detail stages
        if key == KEY_ESC and state == PRESSED:
            self._stage = "menu"
            self._msg = ""
            self._dirty = True
            self._needs_full = True
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
            self._stage = "region"
            self._load_region()
        elif idx == 4:
            self._stage = "about"
        self._dirty = True
        self._needs_full = True

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

    def _load_region(self):
        try:
            data = get(self.ui.api_host, self.ui.api_port, "/api/settings/", timeout=4)
            current = (data or {}).get("region") or ""
            count   = (data or {}).get("region_species_count", 0)
            self._region_input = current
            if current:
                self._msg = "Active: {} ({} spp)".format(current, count)
                self._msg_color = C_OK
            else:
                self._msg = "No region — all species searchable"
                self._msg_color = C_DIM
        except Exception:
            self._region_input = ""
            self._msg = "Could not load region"
            self._msg_color = C_ERR

    def _save_region(self):
        region = self._region_input.strip().upper()
        self._msg = "Saving..." if region else "Clearing..."
        self._msg_color = C_DIM
        self._dirty = True
        self.draw()
        try:
            result = patch(self.ui.api_host, self.ui.api_port,
                           "/api/settings/", {"region": region}, timeout=15)
            if result and result.get("ok"):
                saved = result.get("region", "")
                count = result.get("species_count", 0)
                self._region_input = saved
                if saved:
                    self._msg = "Saved! {} species loaded".format(count)
                    self._msg_color = C_OK
                else:
                    self._msg = "Cleared — all species searchable"
                    self._msg_color = C_OK
            else:
                err = (result or {}).get("error", "Unknown error")
                self._msg = err[:46]
                self._msg_color = C_ERR
        except Exception as e:
            self._msg = str(e)[:46]
            self._msg_color = C_ERR
        self._dirty = True

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
