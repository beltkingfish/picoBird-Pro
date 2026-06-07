"""
STM32 keyboard driver for PicoCalc.
Hardware: I2C1, SDA=GP6, SCL=GP7, address=0x1F
FIFO register 0x09 returns (state, key) pairs.
"""
import machine
import time

KB_ADDR = 0x1F
REG_FIF = 0x09

# Key states
IDLE     = 0
PRESSED  = 1
HOLD     = 2
RELEASED = 3

# Special key codes (keyboard arrows / function keys)
KEY_ENTER     = 0x0A
KEY_ESC       = 0xB1
KEY_UP        = 0xB5
KEY_DOWN      = 0xB6
KEY_LEFT      = 0xB4
KEY_RIGHT     = 0xB7
KEY_BACKSPACE = 0x08

# Joystick codes returned by the STM32
JOY_UP     = 0x01
JOY_DOWN   = 0x02
JOY_LEFT   = 0x03
JOY_RIGHT  = 0x04
JOY_CENTER = 0x05  # joystick press = Enter

# Map joystick codes → arrow/enter equivalents so all screens work with
# either the keyboard arrows or the joystick without extra logic.
_JOY_MAP = {
    JOY_UP:     KEY_UP,
    JOY_DOWN:   KEY_DOWN,
    JOY_LEFT:   KEY_LEFT,
    JOY_RIGHT:  KEY_RIGHT,
    JOY_CENTER: KEY_ENTER,
}


class Keyboard:
    def __init__(self):
        self._i2c = machine.I2C(1, sda=machine.Pin(6), scl=machine.Pin(7), freq=100_000)
        time.sleep_ms(100)

    def read(self):
        """
        Return (state, key) normalised so that joystick events are remapped to
        the equivalent arrow/enter key codes.  Returns (IDLE, 0) when empty.
        """
        try:
            data = self._i2c.readfrom_mem(KB_ADDR, REG_FIF, 2)
            state = data[0]
            key   = data[1]
            if state == IDLE and key == 0:
                return (IDLE, 0)
            # Remap joystick → keyboard equivalent
            key = _JOY_MAP.get(key, key)
            return (state, key)
        except OSError:
            return (IDLE, 0)

    def scan(self):
        """Return list of I2C addresses found — useful for debugging."""
        return self._i2c.scan()

    def get_char(self):
        """Return printable ASCII character on PRESSED, else None."""
        state, key = self.read()
        if state == PRESSED and 0x20 <= key <= 0x7E:
            return chr(key)
        return None
