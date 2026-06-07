"""
Top-level UI controller — owns the screen stack and main loop.
"""
import time
from app.screen import ScreenStack
from app.screens.home import HomeScreen

CHAR_W = 6  # 5 px glyph + 1 px gap
CHAR_H = 8

# Colors (r, g, b)
C_BG    = (0, 0, 0)
C_FG    = (255, 255, 255)
C_GREEN = (80, 200, 120)
C_RED   = (255, 80, 80)
C_DIM   = (100, 100, 100)


class UI:
    def __init__(self, display, kb, api_host, api_port, connected=True):
        self.display   = display
        self.kb        = kb
        self.api_host  = api_host
        self.api_port  = api_port
        self.connected = connected
        self.stack     = ScreenStack(display, kb)

    def run(self):
        self.stack.push(HomeScreen(self))
        while True:
            self.stack.tick()
            time.sleep_ms(50)
