"""
ScrollableListScreen — shared base for full-screen scrolling lists.

Subclasses set TITLE / FOOTER / SELECTABLE and implement load() to populate
self._items (display strings) and optionally self._data (parallel objects).
Override on_select(index) to react to ENTER when SELECTABLE is True.
"""
from app.screen import Screen
from lib.keyboard import PRESSED, HOLD, KEY_ESC, KEY_UP, KEY_DOWN, KEY_ENTER
from app import theme as T

CHAR_W = 6  # 5px glyph + 1px gap


class ScrollableListScreen(Screen):
    TITLE      = ""
    FOOTER     = "Up/Dn=scroll  Esc=back"
    SELECTABLE = False

    def __init__(self, ui):
        super().__init__(ui)
        self._items     = []   # list of display strings
        self._data      = []   # parallel list of source objects (optional)
        self._sel       = 0
        self._off       = 0
        self._dirty     = True
        self._error     = ""
        self._empty_msg = ""

    def on_enter(self):
        self._dirty = True
        self.load()

    # ── Subclass hooks ────────────────────────────────────────────────────────
    def load(self):
        """Populate self._items / self._data / self._error / self._empty_msg."""
        pass

    def on_select(self, index):
        """Called on ENTER over a row when SELECTABLE is True."""
        pass

    # ── Rendering ─────────────────────────────────────────────────────────────
    def draw(self):
        if not self._dirty:
            return
        d = self.ui.display
        d.fill(*T.C_BG)

        d.text(self.TITLE, 10, 8, fg=T.C_HEADER)
        if self._items:
            cx = 10 + (len(self.TITLE) + 1) * CHAR_W
            d.text("({})".format(len(self._items)), cx, 8, fg=T.C_DIM)

        if self._error:
            d.text(self._error[:50], 10, T.LIST_Y, fg=T.C_ERR)
            if self._empty_msg:
                d.text(self._empty_msg[:50], 10, T.LIST_Y + 14, fg=T.C_WARN)
        elif self._empty_msg:
            for i, line in enumerate(self._empty_msg.split("\n")[:3]):
                d.text(line[:50], 10, T.LIST_Y + i * 14, fg=T.C_EMPTY)
        else:
            for i in range(T.LIST_VISIBLE):
                idx = self._off + i
                if idx >= len(self._items):
                    break
                fg = T.C_SEL if idx == self._sel else T.C_FG
                d.text(self._items[idx][:50], 10, T.LIST_Y + i * T.LIST_ROW_H, fg=fg)

        d.text(self.FOOTER, 4, T.FOOTER_Y, fg=T.C_DIM)
        self._dirty = False

    # ── Input ─────────────────────────────────────────────────────────────────
    def on_key(self, state, key):
        if state not in (PRESSED, HOLD):
            return
        if key == KEY_ESC and state == PRESSED:
            self.ui.stack.pop()
        elif key == KEY_ENTER and state == PRESSED and self.SELECTABLE and self._data:
            if 0 <= self._sel < len(self._data):
                self.on_select(self._sel)
        elif key == KEY_UP and self._sel > 0:
            self._sel -= 1
            if self._sel < self._off:
                self._off = self._sel
            self._dirty = True
        elif key == KEY_DOWN and self._sel < len(self._items) - 1:
            self._sel += 1
            if self._sel >= self._off + T.LIST_VISIBLE:
                self._off = self._sel - T.LIST_VISIBLE + 1
            self._dirty = True
