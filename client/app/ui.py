"""Simple screen-stack UI manager."""

import time
from app.screen import Screen
from lib.keyboard import Keyboard, KEY_NONE
from lib.http_client import HTTPClient


class UI:
    def __init__(self, screen: Screen, keyboard: Keyboard,
                 server_host: str, server_port: int):
        self.screen   = screen
        self.keyboard = keyboard
        self.http     = HTTPClient(server_host, server_port)
        self._stack: list = []
        self.running  = False

    # ------------------------------------------------------------------
    # Screen stack
    # ------------------------------------------------------------------

    def push(self, screen_obj):
        self._stack.append(screen_obj)
        screen_obj.on_enter()
        screen_obj.draw()
        self.screen.show()

    def pop(self):
        if len(self._stack) > 1:
            self._stack.pop().on_exit()
            top = self._stack[-1]
            top.on_enter()
            top.draw()
            self.screen.show()

    def replace(self, screen_obj):
        if self._stack:
            self._stack.pop().on_exit()
        self._stack.append(screen_obj)
        screen_obj.on_enter()
        screen_obj.draw()
        self.screen.show()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        self.running = True
        while self.running and self._stack:
            key, mod = self.keyboard.read_key()
            if key != KEY_NONE:
                self._stack[-1].handle_key(key, mod)
                self.screen.show()
            time.sleep_ms(20)

    def quit(self):
        self.running = False
