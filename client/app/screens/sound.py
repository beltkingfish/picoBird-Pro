"""Sound ID screen — record audio and send to BirdNET.

NOTE: Audio recording on the Pico 2 W requires an I2S mic (e.g. INMP441).
This screen assumes the mic is wired up and a record() helper is available.
If no mic is present it shows a friendly error.
"""

from app.screen import WHITE, BLACK, ACCENT, GRAY, GREEN, RED, YELLOW
from lib.keyboard import KEY_ENTER, KEY_ESC

REC_SECONDS = 3


def _record_wav(seconds: int = 3) -> bytes | None:
    """Record *seconds* of mono 22050 Hz audio via I2S and return WAV bytes."""
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

        # Wrap in a minimal WAV header.
        data_len  = len(buf)
        riff_len  = 36 + data_len
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", riff_len, b"WAVE",
            b"fmt ", 16, 1, 1, RATE, RATE * 2, 2, 16,
            b"data", data_len,
        )
        return header + bytes(buf)
    except Exception:
        return None


class SoundScreen:
    def __init__(self, ui):
        self.ui      = ui
        self.screen  = ui.screen
        self.results = []
        self._state  = "ready"  # ready | recording | results | error

    def on_enter(self):
        self.draw()

    def on_exit(self):
        pass

    def draw(self):
        s = self.screen
        s.fill(BLACK)
        s.header("Sound ID")

        if self._state == "ready":
            s.text_center("Press ENTER to record", 80, WHITE)
            s.text_center(f"{REC_SECONDS}s clip sent to BirdNET", 96, GRAY)

        elif self._state == "recording":
            s.text_center("Recording...", 80, RED)
            s.text_center(f"{REC_SECONDS} seconds", 96, GRAY)

        elif self._state == "results":
            s.text("Detections:", 4, 16, ACCENT)
            if self.results:
                for i, det in enumerate(self.results[:8]):
                    y    = 28 + i * 18
                    name = det.get("common_name", "")[:22]
                    conf = int(det.get("confidence", 0) * 100)
                    s.text(f"{name:<22} {conf:3}%", 4, y, WHITE)
            else:
                s.text_center("No birds detected", 100, GRAY)

        elif self._state == "error":
            s.text_center("No microphone found", 80, RED)
            s.text_center("Needs I2S mic (INMP441)", 96, GRAY)

        s.status_bar("ENTER=record  ESC=back")

    def handle_key(self, key: int, mod: int):
        if key == KEY_ESC:
            self.ui.pop()
        elif key == KEY_ENTER:
            self._do_record()

    def _do_record(self):
        s = self.screen
        self._state = "recording"
        self.draw()
        s.show()

        wav = _record_wav(REC_SECONDS)
        if wav is None:
            self._state = "error"
            self.draw()
            return

        # Send to server — multipart/form-data is complex on bare MicroPython,
        # so we POST the raw WAV with Content-Type audio/wav.
        try:
            body = wav
            resp_bytes = self.ui.http._request(
                "POST", "/api/sound/identify",
                body=body, content_type="audio/wav"
            )
            import json
            data         = json.loads(resp_bytes)
            self.results = data.get("detections", [])
            self._state  = "results"
        except Exception as e:
            self._state = "error"
            s.status_bar(f"Server error: {e}")

        self.draw()
