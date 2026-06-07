"""Sound ID screen — record audio and send to BirdNET.

NOTE: Audio recording on the Pico 2 W requires an I2S mic (e.g. INMP441).
This screen is a forward-looking stub: with no mic wired up it shows a
friendly message. It is not yet wired into the home menu.
"""
import json
from app.screen import Screen
from app import theme as T
from lib.keyboard import PRESSED, KEY_ENTER, KEY_ESC

REC_SECONDS = 3


def _record_wav(seconds=3):
    """Record *seconds* of mono 22050 Hz audio via I2S and return WAV bytes.

    Returns None if no I2S mic is present (the common case today).
    """
    try:
        from machine import I2S, Pin
        import struct

        I2S_ID  = 0
        SCK_PIN = 10
        WS_PIN  = 11
        SD_PIN  = 12
        RATE    = 22050
        SAMPLES = RATE * seconds

        audio_in = I2S(
            I2S_ID,
            sck=Pin(SCK_PIN),
            ws=Pin(WS_PIN),
            sd=Pin(SD_PIN),
            mode=I2S.RX,
            bits=16,
            format=I2S.MONO,
            rate=RATE,
            ibuf=4096,
        )
        buf = bytearray(SAMPLES * 2)
        audio_in.readinto(buf)
        audio_in.deinit()

        data_len = len(buf)
        riff_len = 36 + data_len
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", riff_len, b"WAVE",
            b"fmt ", 16, 1, 1, RATE, RATE * 2, 2, 16,
            b"data", data_len,
        )
        return header + bytes(buf)
    except Exception:
        return None


class SoundScreen(Screen):
    def __init__(self, ui):
        super().__init__(ui)
        self.results = []
        self._state  = "ready"   # ready | recording | results | error
        self._dirty  = True

    def on_enter(self):
        self._dirty = True

    def draw(self):
        if not self._dirty:
            return
        d = self.ui.display
        d.fill(*T.BLACK)
        d.text("Sound ID", 10, 8, fg=T.ACCENT)
        d.fill_rect(0, 24, T.WIDTH, 1, 40, 100, 60)

        if self._state == "ready":
            d.text("Press ENTER to record", 10, 60, fg=T.WHITE)
            d.text("{}s clip sent to BirdNET".format(REC_SECONDS), 10, 76, fg=T.GRAY)
        elif self._state == "recording":
            d.text("Recording...", 10, 60, fg=T.RED)
            d.text("{} seconds".format(REC_SECONDS), 10, 76, fg=T.GRAY)
        elif self._state == "results":
            d.text("Detections:", 10, 40, fg=T.ACCENT)
            if self.results:
                for i, det in enumerate(self.results[:10]):
                    y    = 56 + i * 14
                    name = det.get("common_name", "")[:30]
                    conf = int(det.get("confidence", 0) * 100)
                    d.text("{} {}%".format(name, conf), 10, y, fg=T.WHITE)
            else:
                d.text("No birds detected", 10, 60, fg=T.GRAY)
        elif self._state == "error":
            d.text("No microphone found", 10, 60, fg=T.RED)
            d.text("Needs I2S mic (INMP441)", 10, 76, fg=T.GRAY)

        d.text("ENTER=record  ESC=back", 4, T.FOOTER_Y, fg=T.GRAY)
        self._dirty = False

    def on_key(self, state, key):
        if state != PRESSED:
            return
        if key == KEY_ESC:
            self.ui.stack.pop()
        elif key == KEY_ENTER:
            self._do_record()

    def _do_record(self):
        self._state = "recording"
        self._dirty = True
        self.draw()  # paint the recording state immediately

        wav = _record_wav(REC_SECONDS)
        if wav is None:
            self._state = "error"
            self._dirty = True
            return

        # Sending raw WAV requires a binary POST helper; not implemented until
        # mic hardware exists. For now, treat a successful capture as no-result.
        self.results = []
        self._state  = "results"
        self._dirty  = True
