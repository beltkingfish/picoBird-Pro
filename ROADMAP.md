# picoBird Pro — Planned Features & Roadmap

This file tracks planned improvements and future versions of picoBird Pro.

---

## Version 2 — GPIO Expansion Board

The goal of v2 is a custom GPIO hat that sits on top of the Pi 5 inside
the enclosure, replacing all loose jumper wires with a single clean PCB.

### Hardware on the board

| Component | Purpose | Interface | Estimated cost |
|---|---|---|---|
| u-blox NEO-6M (or NEO-M8N) | GPS location tracking | UART | ~$10–25 |
| INMP441 | I2S microphone for sound ID | I2S | ~$5 |
| Waveshare 2.9" e-ink connector | Clean e-ink wiring | SPI (passthrough) | — |
| Momentary push button | Field reset | GPIO 26 | ~$1 |
| Status LED (optional) | Visual boot/error indicator | GPIO | ~$1 |

### New software features enabled by v2

#### Passive sound identification
- Pi 5 continuously records 3-second audio clips via the I2S mic
- BirdNET-Analyzer (already installed) analyzes each clip automatically
- Detections above a confidence threshold are pushed to the PicoCalc
  display in real time as the user walks through a habitat
- No button press required — just walk and watch the screen

#### GPS location tracking
- A new `server/gps.py` service reads NMEA sentences from the GPS module
- Exposes a `/api/location` endpoint returning current lat/lng/accuracy
- Every observation and session is automatically geo-tagged
- Nearby species from eBird auto-populate based on actual GPS position
  (no need to enter a location manually)
- Session summary includes a bounding box of the walk

#### Combined passive logging
- Walk a transect — the Pi 5 listens, identifies, and geo-tags everything
- At the end of the session the PicoCalc shows a complete georeferenced
  species list with timestamps and confidence scores
- Data can be exported as a standard eBird checklist format

### Planned API additions

| Method | Path | Description |
|---|---|---|
| GET | `/api/location` | Current GPS fix (lat, lng, accuracy, satellites) |
| GET | `/api/location/track` | GPS track for current session |
| POST | `/api/sound/listen` | Start/stop continuous passive listening |
| GET | `/api/sound/detections` | Recent BirdNET detections (passive mode) |

### PCB design notes

- Standard Raspberry Pi HAT form factor (65 × 56 mm)
- 40-pin GPIO passthrough header so other HATs can still stack
- JST connector for the e-ink FPC cable
- SMA antenna connector for external GPS antenna (useful inside an
  enclosure where the ceramic patch antenna may have weak signal)
- I2S mic on the board edge with a small drilled hole in the enclosure
  lid for sound ingress
- Reset button routed to a panel-mount connector for the enclosure button

---

## Other Planned Improvements

### USB serial fallback
If WiFi is unavailable, the PicoCalc can fall back to communicating with
the Pi 5 over USB serial using a lightweight request/response protocol.
The Pi 5 would run a serial bridge translating commands into API calls.

### Per-user life lists
Currently all connected PicoCalcs share one life list and observation log.
Adding a `user_id` field to observations and the life list would allow
multiple birders on the same trip to maintain separate records.

### eBird checklist export
Export a session's observations as a properly formatted eBird checklist
that can be submitted directly to eBird via the API.

### Offline map tiles
Cache a small set of OpenStreetMap tiles for the local area on the Pi 5
SD card so a basic map can be shown on the PicoCalc without internet.

### Battery level indicator
If a smart USB-C powerbank with PD communication is used, read the
battery percentage and show it on the e-ink vitals display and PicoCalc
status bar.
