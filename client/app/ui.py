"""
Top-level UI controller — owns the screen stack and main loop.
"""
import time
from app.screen import ScreenStack
from app.screens.home import HomeScreen
from app.http import get


class UI:
    def __init__(self, display, kb, api_host, api_port, connected=True, ap_ssid=""):
        self.display        = display
        self.kb             = kb
        self.api_host       = api_host
        self.api_port       = api_port
        self.connected      = connected
        self.ap_ssid        = ap_ssid
        self.active_session = None   # dict of the running session, or None
        self.stack          = ScreenStack(display, kb)

    def wifi_connected(self):
        """True if the STA interface is currently associated with an AP."""
        try:
            import network
            return network.WLAN(network.STA_IF).isconnected()
        except Exception:
            return False

    def ping_server(self, timeout=3):
        """Ping the API. Updates and returns self.connected so the UI can
        recover from a dropped link/server without a reboot."""
        if not self.wifi_connected():
            self.connected = False
            return False
        try:
            r = get(self.api_host, self.api_port, "/api/ping", timeout=timeout)
            self.connected = bool(r and r.get("status") == "ok")
        except Exception:
            self.connected = False
        return self.connected

    def run(self):
        self.stack.push(HomeScreen(self))
        while True:
            self.stack.tick()
            time.sleep_ms(50)
