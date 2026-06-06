"""SD card SPI driver for MicroPython (PicoCalc wiring)."""

import time
from micropython import const

_CMD0  = const(0x40)
_CMD8  = const(0x48)
_CMD17 = const(0x51)
_CMD24 = const(0x58)
_CMD55 = const(0x77)
_ACMD41 = const(0x69)
_CMD58 = const(0x7A)
_CMD59 = const(0x7B)  # CRC on/off

_R1_IDLE = const(0x01)
_BLOCK   = const(512)


class SDCard:
    def __init__(self, spi, cs):
        self.spi = spi
        self.cs  = cs
        self._buf = bytearray(1)
        self._init_sd()

    def _cs(self, val: int):
        self.cs.value(val)

    def _xfer(self, data: int) -> int:
        self._buf[0] = data
        self.spi.write_readinto(self._buf, self._buf)
        return self._buf[0]

    def _cmd(self, cmd: int, arg: int = 0, crc: int = 0x01) -> int:
        self._cs(0)
        self._xfer(cmd | 0x40)
        self._xfer((arg >> 24) & 0xFF)
        self._xfer((arg >> 16) & 0xFF)
        self._xfer((arg >>  8) & 0xFF)
        self._xfer( arg        & 0xFF)
        self._xfer(crc)
        # Wait for response (up to 8 bytes)
        for _ in range(8):
            r = self._xfer(0xFF)
            if r != 0xFF:
                return r
        return 0xFF

    def _init_sd(self):
        # Send 80 clocks with CS high to wake card.
        self._cs(1)
        for _ in range(10):
            self._xfer(0xFF)

        # Reset.
        for _ in range(5):
            r = self._cmd(_CMD0, 0, 0x95)
            if r == _R1_IDLE:
                break
        else:
            raise OSError("SD card not responding")

        # CMD8 — check voltage range (SDHC support).
        r = self._cmd(_CMD8, 0x000001AA, 0x87)
        if r == _R1_IDLE:
            for _ in range(4):
                self._xfer(0xFF)

        # ACMD41 — initialise.
        deadline = time.time() + 2
        while time.time() < deadline:
            self._cmd(_CMD55, 0)
            r = self._cmd(_ACMD41, 0x40000000)
            if r == 0:
                break
        else:
            raise OSError("SD card init timeout")

        self._cs(1)
        self._xfer(0xFF)

    def readblocks(self, block_num: int, buf: bytearray):
        for i in range(len(buf) // _BLOCK):
            self._read_block(block_num + i, buf, i * _BLOCK)

    def writeblocks(self, block_num: int, buf: bytearray):
        for i in range(len(buf) // _BLOCK):
            self._write_block(block_num + i, buf, i * _BLOCK)

    def ioctl(self, op, arg):
        if op == 4:   # BP_IOCTL_SEC_COUNT
            return 0
        if op == 5:   # BP_IOCTL_SEC_SIZE
            return _BLOCK
        return None

    def _read_block(self, num: int, buf: bytearray, offset: int):
        r = self._cmd(_CMD17, num)
        if r != 0:
            raise OSError(f"CMD17 failed: {r}")
        # Wait for data token 0xFE.
        for _ in range(1024):
            if self._xfer(0xFF) == 0xFE:
                break
        else:
            raise OSError("SD read timeout")
        mv = memoryview(buf)[offset:offset + _BLOCK]
        self.spi.readinto(mv, 0xFF)
        self._xfer(0xFF)  # CRC (ignored)
        self._xfer(0xFF)
        self._cs(1)
        self._xfer(0xFF)

    def _write_block(self, num: int, buf: bytearray, offset: int):
        r = self._cmd(_CMD24, num)
        if r != 0:
            raise OSError(f"CMD24 failed: {r}")
        self._xfer(0xFE)  # Data token
        self.spi.write(memoryview(buf)[offset:offset + _BLOCK])
        self._xfer(0xFF)  # CRC
        self._xfer(0xFF)
        # Wait for write to complete.
        for _ in range(1024):
            if self._xfer(0xFF) == 0xFF:
                break
        self._cs(1)
        self._xfer(0xFF)
