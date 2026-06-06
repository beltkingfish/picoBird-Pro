"""PicoCalc STM32 keyboard driver (I2C, address 0x08)."""

from micropython import const

_KBD_ADDR = const(0x08)
_REG_KEY  = const(0x00)

# Special key codes returned by the STM32 firmware.
KEY_NONE  = 0x00
KEY_UP    = 0x01
KEY_DOWN  = 0x02
KEY_LEFT  = 0x03
KEY_RIGHT = 0x04
KEY_ENTER = 0x0D
KEY_ESC   = 0x1B
KEY_BKSP  = 0x08
KEY_TAB   = 0x09


class Keyboard:
    def __init__(self, i2c, addr: int = _KBD_ADDR):
        self.i2c  = i2c
        self.addr = addr
        self._buf = bytearray(2)

    def read_key(self) -> tuple[int, int]:
        """
        Poll the keyboard controller.
        Returns (keycode, modifiers).
        keycode 0 means no key pressed.
        """
        try:
            self.i2c.readfrom_into(self.addr, self._buf)
        except OSError:
            return KEY_NONE, 0
        return self._buf[0], self._buf[1]

    def get_char(self) -> str | None:
        """Return a printable character, or None if no key / special key."""
        code, _mod = self.read_key()
        if code == KEY_NONE:
            return None
        if 0x20 <= code <= 0x7E:
            return chr(code)
        return None

    def wait_key(self, timeout_ms: int = 5000) -> int:
        """Block until a key is pressed or timeout expires. Returns keycode."""
        import time
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            code, _ = self.read_key()
            if code != KEY_NONE:
                return code
            time.sleep_ms(20)
        return KEY_NONE
