# picoBird Pro

A two-device birding field guide built for the field:

| Device | Role |
|---|---|
| **Raspberry Pi 5** (8 GB) | Backend: SQLite, eBird API v2, BirdNET sound ID, WiFi AP |
| **ClockworkPi PicoCalc** (Pico 2 W + ILI9488 320×320) | Client: display + keyboard, talks to Pi over WiFi |

---

## Features

- **Species search** — full-text search across the complete eBird taxonomy (~16,000 species)
- **Log sightings** — one-press quick-log or a full form with notes/count/date
- **My Sightings** — browse all logged observations, tap for detail
- **Life List** — auto-maintained list of every unique species ever logged
- **Sound ID** — record audio via a Rode Wireless Pro USB mic plugged into the Pi; BirdNET identifies the calls
- **Offline-aware** — graceful messaging when WiFi drops; reconnects automatically
- **Secure AP** — gunicorn binds only to the local AP address (`192.168.4.1`) and loopback; WPA2 CCMP only

---

## Architecture

```
PicoCalc  ───[WiFi 192.168.4.x]───>  Pi 5 AP (192.168.4.1:5000)
  MicroPython client                     Flask / SQLite / BirdNET
  - species search                        - eBird taxonomy cache (FTS5)
  - log observations                      - life list (trigger-maintained)
  - browse life list                      - BirdNET-Analyzer inference
  - sound ID (USB mic on Pi)              - USB audio capture via arecord
```

---

## Repository layout

```
picoBird-Pro/
├── server/
│   ├── main.py               # App factory, blueprint registration
│   ├── database.py           # SQLite schema + query helpers
│   ├── ebird_api.py          # eBird API v2 client (TTL-cached)
│   ├── birdnet.py            # BirdNET-Analyzer subprocess wrapper
│   ├── audio.py              # USB mic discovery + arecord capture
│   ├── passive_listener.py   # Background 5s-chunk BirdNET daemon
│   ├── vitals.py             # System stats for e-ink display
│   └── api/
│       ├── _validation.py    # Shared input clamping helpers
│       ├── species.py        # Search, sync taxonomy, nearby
│       ├── observations.py   # CRUD for logged birds
│       ├── lifelist.py       # Life list + stats
│       └── sound.py          # USB capture, passive listen, WAV upload
├── client/
│   ├── main.py               # Boot: load config, connect WiFi, launch UI
│   ├── config.json           # WiFi + API host (edit without reflashing)
│   ├── lib/
│   │   ├── ili9488.py        # ILI9488 SPI display driver (RGB666, SPI1)
│   │   └── keyboard.py       # STM32 I2C keyboard + joystick driver
│   └── app/
│       ├── theme.py          # Centralized colours and layout constants
│       ├── screen.py         # Screen base + stack manager
│       ├── ui.py             # UI manager (WiFi check, ping helper)
│       ├── http.py           # Hardened raw-socket HTTP client
│       └── screens/
│           ├── _list.py       # ScrollableListScreen base class
│           ├── home.py        # Main menu + connection status
│           ├── search.py      # Species search (paginated)
│           ├── species_detail.py  # Detail view + quick-log (L key)
│           ├── log_sighting.py    # Full log form (non-blocking close)
│           ├── today.py       # My Sightings browser
│           ├── lifelist.py    # Life list browser
│           └── sound.py       # Sound ID (USB mic on Pi 5)
└── setup/
    ├── install.sh             # Full Pi 5 setup script (interactive)
    ├── preflight.py           # Taxonomy sync with retry
    ├── picobird-pro.service   # Gunicorn systemd unit
    ├── picobird-pre.service   # Pre-flight (taxonomy sync) unit
    └── picobird-wlan-ip.service  # Assigns 192.168.4.1 before AP starts
```

---

## Pi 5 Setup

### 1. Flash & SSH in

Flash **Raspberry Pi OS Lite (64-bit)** to an SD card. Boot, SSH in as your user.

### 2. Install git

Raspberry Pi OS Lite doesn't include git by default:

```bash
sudo apt update && sudo apt install -y git
```

### 3. Clone the repo

```bash
sudo git clone https://github.com/beltkingfish/picobird-pro /opt/picobird-pro-src
```

### 4. Run the installer

```bash
cd /opt/picobird-pro-src
sudo bash setup/install.sh
```

The installer is interactive. It will prompt you for:

| Prompt | Notes |
|---|---|
| **eBird API key** | Get one free at [ebird.org/api/keygen](https://ebird.org/api/keygen). The installer validates it with a live API call and re-prompts on failure. |
| **WiFi password** | Password for the `picoBirdPro` AP. A secure random default is suggested. |

Then it automatically:
- Detects your WiFi interface (no hardcoded `wlan0`)
- Installs `hostapd` + `dnsmasq` and configures the `picoBirdPro` AP (WPA2 CCMP)
- Creates a `picobird-wlan-ip` systemd service to assign `192.168.4.1/24`
- Configures NetworkManager to leave the AP interface alone
- Clones BirdNET-Analyzer to `/opt/BirdNET-Analyzer`
- Creates a Python venv with Flask, Gunicorn, and all dependencies
- Writes secrets (`/etc/hostapd/hostapd.conf`, systemd override) as `root:root 600`
- Enables and starts `picobird-pro`, `picobird-pre`, `picobird-wlan-ip`
- Sets up logrotate for access/error logs

### 5. Verify

```bash
# API up?
curl http://127.0.0.1:5000/api/ping
# → {"status": "ok"}

# Taxonomy loaded?
curl "http://127.0.0.1:5000/api/species/search?q=robin&page=0"
```

If the taxonomy is empty, trigger a manual sync:

```bash
curl -X POST http://127.0.0.1:5000/api/species/sync
```

### 6. (Optional) Override USB audio device

The installer writes `AUDIO_DEVICE=` (empty) to the service environment. With the
Rode Wireless Pro receiver plugged in, the server auto-detects it. To force a
specific ALSA device:

```bash
sudo systemctl edit picobird-pro
```

Add (replacing `hw:1,0` with your device from `arecord -l`):
```ini
[Service]
Environment=AUDIO_DEVICE=hw:1,0
```

---

## PicoCalc Setup

### 1. Flash MicroPython

Flash the latest [MicroPython for Pico 2 W](https://micropython.org/download/RPI_PICO2_W/) to the PicoCalc.

### 2. Configure WiFi

Edit `client/config.json` before copying:

```json
{
    "ap_ssid": "picoBirdPro",
    "ap_password": "your-ap-password",
    "api_host": "192.168.4.1",
    "api_port": 5000
}
```

Use whatever password you set during the installer.

### 3. Copy client files

```bash
mpremote connect /dev/ttyACM0 cp -r client/. :
```

Or use Thonny to copy the `client/` directory to the root of the Pico.

### 4. Verify wiring (PicoCalc default pins)

| Component | Pins |
|---|---|
| ILI9488 display | SPI1: SCK=GP10, MOSI=GP11, CS=GP13, DC=GP14, RST=GP15, BL=GP12 |
| STM32 keyboard | I2C1: SDA=GP6, SCL=GP7, addr=0x1F |

These match the PicoCalc hardware — no changes needed unless you have a modified board.

### 5. Boot

Power cycle the PicoCalc. It will:
1. Init the ILI9488 display (RGB666, 18-bit)
2. Scan for and connect to the `picoBirdPro` AP
3. Show the home screen with connection status

---

## Sound ID (Rode Wireless Pro)

1. Plug the Rode Wireless Pro USB receiver into the Pi 5.
2. The Pi auto-detects it via `arecord -l` (no config needed).
3. On the PicoCalc, open **Sound ID** from the main menu.
4. The screen shows the detected mic and offers:
   - **Listen 10s / 30s** — on-demand capture + BirdNET analysis
   - **Passive On/Off** — continuous background detection (5s chunks, last 50 results kept)
   - **View Detections** — browse passive results with species name, confidence %, and time

Results are **show-only** — Sound ID detections are not written to your sighting log.

---

## E-ink status display (Waveshare 2.9" V2)

An optional Waveshare 2.9" V2 (296×128, black/white) e-paper panel on the Pi's
GPIO shows a live status dashboard, refreshed every 30 s by the `picobird-vitals`
service: title bar + AP IP, uptime, AP client count, server/BirdNET status, CPU
temp, memory, life-list count, observations today, and the last bird logged.

### Wiring (BCM numbering)

| E-ink pin | Pi GPIO (BCM) | Physical pin |
|---|---|---|
| VCC | 3.3 V | 1 |
| GND | GND | 6 |
| DIN | GPIO 10 (SPI0 MOSI) | 19 |
| CLK | GPIO 11 (SPI0 SCLK) | 23 |
| CS | GPIO 8 (SPI0 CE0) | 24 |
| DC | GPIO 25 | 22 |
| RST | GPIO 17 | 11 |
| BUSY | GPIO 24 | 18 |

### Raspberry Pi 5 note

The Pi 5's RP1 GPIO controller is **not** supported by classic `RPi.GPIO`. The
installer installs `python3-rpi-lgpio` (a drop-in `RPi.GPIO` API backed by lgpio)
instead. SPI is enabled automatically (`dtparam=spi=on`).

### Test it

After plugging in the panel, render a single frame:

```bash
sudo -u picobird /opt/picobird-pro/venv/bin/python -m server.vitals --once
```

The panel should do one full refresh and show the dashboard. Then check the
service:

```bash
systemctl status picobird-vitals
journalctl -u picobird-vitals -n 20
```

If you see "running in dry-run mode" in the log, the GPIO library isn't loading —
on a Pi 5 confirm `python3-rpi-lgpio` is installed (`sudo apt install -y
python3-rpi-lgpio`, which removes the incompatible `python3-rpi.gpio`).

---

## Importing your eBird life list

**The eBird API cannot pull your personal life list.** The public API only exposes
shared/public data (observations, hotspots, regions, taxonomy, statistics) — there is
no authenticated "my life list" endpoint, so entering your API key during setup does
**not** import your existing lifers.

To seed your life list, import the CSV eBird lets you download from the website:

1. Go to [ebird.org/lifelist](https://ebird.org/lifelist)
2. Pick the region/time span you want (e.g. **World**, **All years**)
3. Click **Download (CSV)** (top right)
4. Copy the file onto the Pi 5 (e.g. via `scp`), then run:

```bash
python3 /opt/picobird-pro-src/setup/import_lifelist.py ~/ebird_world_life_list.csv
```

It matches each species against the synced taxonomy and adds any missing lifers,
printing `{"added": N, "skipped": M, "unmatched": K}`. Re-running is safe (already
present species are skipped). Make sure the taxonomy is synced first (the installer
does this).

---

## API Reference

| Method | Path | Description |
|---|---|---|
| GET | `/api/ping` | Health check |
| GET | `/api/species/search?q=robin&page=0` | FTS species search |
| GET | `/api/species/<code>` | Species detail |
| POST | `/api/species/sync` | Sync full eBird taxonomy |
| GET | `/api/species/nearby?lat=&lng=&dist=25` | Nearby species from eBird |
| GET | `/api/observations/?limit=100&offset=0` | List observations |
| POST | `/api/observations/` | Log an observation |
| PATCH | `/api/observations/<id>` | Update observation |
| DELETE | `/api/observations/<id>` | Delete observation |
| GET | `/api/sessions/` | List birding sessions |
| POST | `/api/sessions/` | Start a session |
| PATCH | `/api/sessions/<id>/end` | End a session |
| GET | `/api/sessions/<id>/summary` | Session summary (species/obs counts) |
| GET | `/api/lifelist/` | Life list (paginated) |
| GET | `/api/lifelist/stats` | Life list stats |
| POST | `/api/lifelist/import` | Import eBird life-list CSV (multipart `file`) |
| GET | `/api/vitals/` | System + birding stats (for Settings) |
| GET | `/api/sound/device` | Detected USB mic (or null) |
| POST | `/api/sound/capture?duration=10` | Record + BirdNET (3–30 s) |
| POST | `/api/sound/listen` | Start/stop passive listener `{"action":"start"}` |
| GET | `/api/sound/detections` | Recent passive detections |
| POST | `/api/sound/identify` | Upload WAV → BirdNET detections |

---

## WiFi defaults

| Setting | Default |
|---|---|
| SSID | `picoBirdPro` |
| Password | *(set during installer — random default suggested)* |
| Pi 5 IP | `192.168.4.1` |
| Server port | `5000` |

---

## Updating

To pull the latest code and restart the service:

```bash
cd /opt/picobird-pro-src
sudo git pull
sudo systemctl restart picobird-pro
```

Or as a one-liner:

```bash
sudo git -C /opt/picobird-pro-src pull && sudo systemctl restart picobird-pro
```

---

## Development

### Running the tests

The server has a pytest suite covering search (incl. region filtering),
settings, observations, sessions, and life-list CSV import. It uses an isolated
temp SQLite DB and mocks the eBird API, so no hardware or network is needed:

```bash
pip install -r server/requirements-dev.txt
pytest
```

CI runs the same suite on every push and pull request (Python 3.11 and 3.12) via
`.github/workflows/ci.yml`.

---

## License

MIT
