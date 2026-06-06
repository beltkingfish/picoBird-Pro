"""picoBird Pro — physical reset button watcher.

Wires a momentary push button between GPIO 26 and GND.
On press: updates the e-ink display to show 'Restarting...',
restarts the three picoBird services, then lets the vitals
service refresh the display when everything is back up.

Debounce: 500 ms (ignores bounces and accidental brushes).
Long press (3 s): full system reboot instead of service restart.
"""

import os
import time
import signal
import logging
import subprocess

try:
    import RPi.GPIO as GPIO
    _GPIO_OK = True
except ImportError:
    _GPIO_OK = False

BUTTON_PIN    = 26          # BCM numbering; wire to GND via momentary switch
DEBOUNCE_MS   = 500        # ignore edges within this window
LONG_PRESS_S  = 3.0        # hold this long for a full reboot

SERVICES = [
    "picobird-pro",
    "picobird-vitals",
    "picobird-pre",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s button %(message)s")
log = logging.getLogger("button")


def _run(cmd: list[str]) -> bool:
    try:
        subprocess.run(cmd, check=True, timeout=30,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as exc:
        log.error("%s failed: %s", " ".join(cmd), exc)
        return False


def _show_eink_message(line1: str, line2: str = ""):
    """Quick e-ink banner — best-effort, never blocks the restart."""
    try:
        from server.eink import EPD
        from PIL import Image, ImageDraw
        from server.vitals import _load_font

        W, H = 296, 128
        img = Image.new("1", (W, H), 1)
        d   = ImageDraw.Draw(img)
        f14 = _load_font(14)
        f11 = _load_font(11)
        d.rectangle([0, 0, W, H], fill=0)
        d.text((8, 40), line1, font=f14, fill=1)
        if line2:
            d.text((8, 62), line2, font=f11, fill=1)
        d.rectangle([0, 0, W - 1, H - 1], outline=1)

        epd = EPD()
        epd.init()
        epd.display(img.tobytes())
        epd.sleep()
        epd.close()
    except Exception as exc:
        log.warning("e-ink banner skipped: %s", exc)


def _restart_services():
    log.info("Restarting picoBird services...")
    _show_eink_message("Restarting...", "Please wait")
    for svc in SERVICES:
        _run(["systemctl", "restart", svc])
    log.info("Services restarted")


def _full_reboot():
    log.info("Long press detected — rebooting system")
    _show_eink_message("Rebooting...", "")
    time.sleep(1)
    _run(["reboot"])


def _on_press(channel):
    """Edge-detect callback — measures hold duration, acts on release."""
    press_time = time.time()
    # Wait for release (pin goes HIGH again)
    while GPIO.input(BUTTON_PIN) == GPIO.LOW:
        time.sleep(0.05)
        if time.time() - press_time > LONG_PRESS_S + 0.5:
            break  # safety: don't wait forever

    held = time.time() - press_time
    log.info("Button held %.1f s", held)

    if held >= LONG_PRESS_S:
        _full_reboot()
    else:
        _restart_services()


_running = True


def _handle_signal(sig, frame):
    global _running
    _running = False


def run():
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT,  _handle_signal)

    if not _GPIO_OK:
        log.warning("RPi.GPIO not available — running in dry-run mode")
        log.warning("Button watcher is a no-op until GPIO is accessible")
        while _running:
            time.sleep(1)
        return

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Falling edge = button pressed (pin pulled LOW through switch to GND)
    GPIO.add_event_detect(
        BUTTON_PIN,
        GPIO.FALLING,
        callback=_on_press,
        bouncetime=DEBOUNCE_MS,
    )

    log.info("Button watcher ready on GPIO %d (BCM)", BUTTON_PIN)
    log.info("Short press = restart services | Hold %ss = reboot", LONG_PRESS_S)

    try:
        while _running:
            time.sleep(0.5)
    finally:
        GPIO.cleanup()
        log.info("GPIO cleaned up")


if __name__ == "__main__":
    run()
