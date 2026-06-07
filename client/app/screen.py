"""
Screen stack manager. Screens push/pop onto a stack; only the top screen
receives key events and draw calls.
"""


class Screen:
    """Base class for all screens."""

    def __init__(self, ui):
        self.ui = ui

    def on_enter(self):
        pass

    def on_key(self, state, key):
        pass

    def draw(self):
        pass


class ScreenStack:
    def __init__(self, display, kb):
        self.display = display
        self.kb = kb
        self._stack = []

    def push(self, screen):
        self._stack.append(screen)
        screen.on_enter()

    def pop(self):
        if self._stack:
            self._stack.pop()
        if self._stack:
            self._stack[-1].on_enter()

    @property
    def top(self):
        return self._stack[-1] if self._stack else None

    def tick(self):
        state, key = self.kb.read()
        if self.top:
            if state:
                self.top.on_key(state, key)
            self.top.draw()
