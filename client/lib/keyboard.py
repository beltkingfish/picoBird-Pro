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

# Special key codes
KEY_ENTER     = 0x0A
KEY_ESC       = 0xB1
KEY_UP        = 0xB5
KEY_DOWN      = 0xB6
KEY_LEFT      = 0xB4
KEY_RIGHT     = 0xB7
KEY_BACKSPACE = 0x08

# Joystick codes (returned as key when state==PRESSED)
JOY_UP     = 0x01
JOY_DOWN   = 0x02
JOY_LEFT   = 0x03
JOY_RIGHT  = 0x04
JOY_CENTER = 0x05


class Keyboard:
    def __init__(self):
        self._i2c = machine.I2C(1, sda=machine.Pin(6), scl=machine.Pin(7), freq=100_000)
        time.sleep_ms(100)

    def read(self):
        """Return (state, key) or (IDLE, 0) if FIFO empty."""
        try:
            data = self._i2c.readfrom_mem(KB_ADDR, REG_FIF, 2)
            state = data[0]
            key   = data[1]
            if state == IDLE and key == 0:
                return (IDLE, 0)
            return (state, key)
        except OSError:
            return (IDLE, 0)

    def get_char(self):
        """Return printable character or None. Blocks until PRESSED or no key."""
        state, key = self.read()
        if state == PRESSED and 0x20 <= key <= 0x7E:
            return chr(key)
        return None

    def get_key(self):
        """Return raw (state, key) on any event, else (IDLE, 0)."""
        return self.read()
